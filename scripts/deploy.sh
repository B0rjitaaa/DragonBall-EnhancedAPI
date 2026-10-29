#!/usr/bin/env bash
# Actualiza el proyecto y deja los contenedores al día:
#   - git pull (salvo SKIP_PULL=1, p. ej. desde el hook post-merge)
#   - reconstruye imágenes solo si cambian dependencias o Dockerfiles
#   - aplica migraciones y reinicia backend + Celery (Celery no recarga el código solo)
#
# Uso:  scripts/deploy.sh            (o `make deploy`)
#       SKIP_PULL=1 scripts/deploy.sh <commit-anterior>   (lo usa .githooks/post-merge)
set -euo pipefail
cd "$(dirname "$0")/.."

BEFORE="${1:-$(git rev-parse HEAD)}"
if [ "${SKIP_PULL:-0}" != "1" ]; then
  git pull --ff-only
fi
AFTER="$(git rev-parse HEAD)"

if [ "$BEFORE" = "$AFTER" ] && [ "${FORCE:-0}" != "1" ]; then
  echo "✔ No new changes (use FORCE=1 to force it)."
  exit 0
fi

CHANGED="$(git diff --name-only "$BEFORE" "$AFTER" || true)"
changed() { printf '%s\n' "$CHANGED" | grep -qE "$1"; }

if changed '^backend/(requirements\.txt|Dockerfile|entrypoint\.sh)$'; then
  echo "→ Backend dependencies changed: rebuilding the image…"
  docker compose build backend
fi

# Webcam del archivador (solo con COMPOSE_PROFILES=camera).
if changed '^camera/' && docker compose config --services 2>/dev/null | grep -qx camera; then
  echo "→ The webcam service changed: rebuilding…"
  docker compose build camera
fi

# Modo producción (COMPOSE_FILE con docker-compose.prod.yml, p. ej. la Pi): el
# frontend es un build estático dentro de la imagen, así que cualquier cambio
# en frontend/ obliga a reconstruirla.
if docker compose config 2>/dev/null | grep -q "target: prod"; then
  if changed '^frontend/'; then
    echo "→ Frontend changes (production mode): rebuilding the static build…"
    docker compose up -d --build frontend
  fi
elif changed '^frontend/(package(-lock)?\.json|Dockerfile)$'; then
  echo "→ Frontend dependencies changed: rebuilding (with fresh node_modules)…"
  docker compose up -d --build --renew-anon-volumes frontend
fi

echo "→ Starting services…"
docker compose up -d

echo "→ Applying migrations…"
docker compose exec -T backend python manage.py migrate --noinput

echo "→ Restarting the backend, Celery and the scanner to load the new code…"
docker compose restart backend celery_worker celery_beat scanner_worker

echo "→ Cleaning up old images…"
docker image prune -f >/dev/null

echo "✔ Updated to $(git log -1 --format='%h %s')"
