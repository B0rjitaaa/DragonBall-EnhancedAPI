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
  echo "✔ Sin cambios nuevos (usa FORCE=1 para forzar)."
  exit 0
fi

CHANGED="$(git diff --name-only "$BEFORE" "$AFTER" || true)"
changed() { printf '%s\n' "$CHANGED" | grep -qE "$1"; }

if changed '^backend/(requirements\.txt|Dockerfile|entrypoint\.sh)$'; then
  echo "→ Cambian las dependencias del backend: reconstruyendo imagen…"
  docker compose build backend
fi

if changed '^frontend/(package(-lock)?\.json|Dockerfile)$'; then
  echo "→ Cambian las dependencias del frontend: reconstruyendo (con node_modules nuevos)…"
  docker compose up -d --build --renew-anon-volumes frontend
fi

echo "→ Levantando servicios…"
docker compose up -d

echo "→ Aplicando migraciones…"
docker compose exec -T backend python manage.py migrate --noinput

echo "→ Reiniciando backend y Celery para cargar el código nuevo…"
docker compose restart backend celery_worker celery_beat

echo "✔ Actualizado a $(git log -1 --format='%h %s')"
