#!/usr/bin/env bash
# Instalación en un solo paso (make install). En local basta con `docker compose up -d` (todo tiene valores
# por defecto en .env.defaults y se hace solo: catálogo y precios de data/seed/, usuario admin / admin y
# huellas del escáner); este script además espera a que esté listo y lo resume.
#
#   scripts/install.sh                         en tu ordenador (http://localhost:5173, admin / admin)
#   scripts/install.sh --server 192.168.1.50   en un servidor de casa: .env de producción con claves
#                                              aleatorias, nginx, HTTPS y despliegue con git pull
set -euo pipefail
cd "$(dirname "$0")/.."

SERVER_IP=""
if [ "${1:-}" = "--server" ]; then
  SERVER_IP="${2:?Usage: scripts/install.sh --server <server-ip>}"
fi

say() { printf '\n\033[1;33m▶ %s\033[0m\n' "$*"; }
ok() { printf '  \033[32m✔\033[0m %s\n' "$*"; }
die() { printf '\n\033[31m✘ %s\033[0m\n' "$*" >&2; exit 1; }
random() {  # random N: N caracteres aleatorios (hex; sin tuberías que corten con pipefail)
  local s=""
  while [ "${#s}" -lt "$1" ]; do s="$s$(openssl rand -hex 32)"; done
  printf '%s' "${s:0:$1}"
}
set_env() {  # set_env CLAVE valor: cambia la línea (o la añade) en el .env
  if grep -qE "^#? ?$1=" .env; then
    sed -i.bak -E "s|^#? ?$1=.*|$1=$2|" .env && rm -f .env.bak
  else
    printf '%s=%s\n' "$1" "$2" >> .env
  fi
}

say "Checking Docker"
command -v docker >/dev/null || die "Docker is not installed. Install it: https://docs.docker.com/get-docker/"
docker compose version >/dev/null 2>&1 || die "Docker Compose v2 is missing (the \"docker compose\" command)."
docker info >/dev/null 2>&1 || die "Docker is not running (on a Mac, open Docker Desktop)."
ok "$(docker compose version)"

ADMIN_PASSWORD=""
say "Configuration"
if [ -f .env ]; then
  ok "There is already a .env: leaving it as it is"
elif [ -z "$SERVER_IP" ]; then
  ok "No .env needed locally: using the values in .env.defaults"
else
  cp .env.example .env
  ADMIN_PASSWORD="$(random 16)"
  set_env DJANGO_SECRET_KEY "$(random 60)"
  set_env POSTGRES_PASSWORD "$(random 24)"
  set_env DJANGO_SUPERUSER_PASSWORD "$ADMIN_PASSWORD"
  chmod 600 .env
  ok "Created .env with random keys (Django, Postgres and the admin)"
  set_env COMPOSE_FILE "docker-compose.yml:docker-compose.prod.yml"
  set_env DJANGO_DEBUG 0
  set_env DJANGO_ALLOWED_HOSTS "localhost,127.0.0.1,backend,$SERVER_IP"
  set_env DJANGO_CSRF_TRUSTED_ORIGINS "http://$SERVER_IP,https://$SERVER_IP,http://$SERVER_IP:5173"
  set_env BACKUP_DIR_HOST "$HOME/backups/dbs"
  set_env BACKUP_STATUS_FILE /backups/last_status.json
  mkdir -p "$HOME/backups/dbs/request"
  ok "Server mode for $SERVER_IP (nginx on 80/443, gunicorn, backups in ~/backups/dbs)"
fi

say "Building and starting the services (the first time takes a few minutes)"
docker compose up -d --build

say "Waiting for the backend (the first time it imports the catalog and prices from the repository)"
for i in $(seq 1 120); do
  if docker compose exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/fields/', timeout=3)" >/dev/null 2>&1; then
    ok "Backend ready"
    break
  fi
  [ "$i" = 120 ] && die "The backend does not start. See what is going on with: docker compose logs --tail 100 backend"
  sleep 5
done
docker compose exec -T backend python manage.py shell -c "
from cards.models import Card; from prices.models import CardPrice
print(f'  ✔ {Card.objects.count()} cards, {CardPrice.objects.count()} with a price')" 2>/dev/null | tail -1

if [ -n "$SERVER_IP" ]; then
  say "HTTPS for the phone camera"
  scripts/local-https.sh "$SERVER_IP"
  say "Automatic deploy on every git pull"
  git config core.hooksPath .githooks
  ok "Hook enabled"
fi

WEB="http://localhost:5173"; ADMIN="http://localhost:8000/admin/"
if [ -n "$SERVER_IP" ]; then WEB="http://$SERVER_IP"; ADMIN="http://$SERVER_IP/admin/"; fi
if [ -n "$ADMIN_PASSWORD" ]; then
  LOGIN="admin / $ADMIN_PASSWORD   (keep it safe; it is in .env, DJANGO_SUPERUSER_PASSWORD)"
elif [ -f .env ] && grep -q "^DJANGO_SUPERUSER_PASSWORD=" .env; then
  LOGIN="the user and password from DJANGO_SUPERUSER_* in your .env"
else
  LOGIN="admin / admin   (if there was already an administrator, yours)"
fi
say "Done!"
cat <<EOF
  Web:    $WEB
  Wiki:   $WEB/wiki
  Admin:  $ADMIN  →  $LOGIN

  In the background, without you doing anything:
  · the scanner fingerprints are computed (a good while the first time),
  · and every day the cards, the ban list and the prices are brought up to date.
EOF
if [ -n "$SERVER_IP" ]; then
  cat <<EOF

  To finish the server (needs sudo; see the wiki, "Step-by-step installation"):
  · daily backups:
      make backups
  · install $WEB/ca.crt on each phone to use the camera over HTTPS.
EOF
fi
