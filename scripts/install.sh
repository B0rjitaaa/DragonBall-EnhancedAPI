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
  SERVER_IP="${2:?Uso: scripts/install.sh --server <ip-del-servidor>}"
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

say "Comprobando Docker"
command -v docker >/dev/null || die "No está Docker. Instálalo: https://docs.docker.com/get-docker/"
docker compose version >/dev/null 2>&1 || die "Falta Docker Compose v2 (el comando «docker compose»)."
docker info >/dev/null 2>&1 || die "Docker no está arrancado (en el Mac, abre Docker Desktop)."
ok "$(docker compose version)"

ADMIN_PASSWORD=""
say "Configuración"
if [ -f .env ]; then
  ok "Ya hay un .env: se deja como está"
elif [ -z "$SERVER_IP" ]; then
  ok "En local no hace falta .env: se usan los valores de .env.defaults"
else
  cp .env.example .env
  ADMIN_PASSWORD="$(random 16)"
  set_env DJANGO_SECRET_KEY "$(random 60)"
  set_env POSTGRES_PASSWORD "$(random 24)"
  set_env DJANGO_SUPERUSER_PASSWORD "$ADMIN_PASSWORD"
  chmod 600 .env
  ok "Creado .env con claves aleatorias (Django, Postgres y el admin)"
  set_env COMPOSE_FILE "docker-compose.yml:docker-compose.prod.yml"
  set_env DJANGO_DEBUG 0
  set_env DJANGO_ALLOWED_HOSTS "localhost,127.0.0.1,backend,$SERVER_IP"
  set_env DJANGO_CSRF_TRUSTED_ORIGINS "http://$SERVER_IP,https://$SERVER_IP,http://$SERVER_IP:5173"
  set_env BACKUP_DIR_HOST "$HOME/backups/dbs"
  set_env BACKUP_STATUS_FILE /backups/last_status.json
  mkdir -p "$HOME/backups/dbs/request"
  ok "Modo servidor para $SERVER_IP (nginx en el 80/443, gunicorn, copias en ~/backups/dbs)"
fi

say "Construyendo y arrancando los servicios (la primera vez tarda unos minutos)"
docker compose up -d --build

say "Esperando al backend (la primera vez importa el catálogo y los precios del repositorio)"
for i in $(seq 1 120); do
  if docker compose exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/fields/', timeout=3)" >/dev/null 2>&1; then
    ok "Backend listo"
    break
  fi
  [ "$i" = 120 ] && die "El backend no arranca. Mira qué pasa con: docker compose logs --tail 100 backend"
  sleep 5
done
docker compose exec -T backend python manage.py shell -c "
from cards.models import Card; from prices.models import CardPrice
print(f'  ✔ {Card.objects.count()} cartas, {CardPrice.objects.count()} con precio')" 2>/dev/null | tail -1

if [ -n "$SERVER_IP" ]; then
  say "HTTPS para la cámara del móvil"
  scripts/local-https.sh "$SERVER_IP"
  say "Despliegue automático en cada git pull"
  git config core.hooksPath .githooks
  ok "Hook activado"
fi

WEB="http://localhost:5173"; ADMIN="http://localhost:8000/admin/"
if [ -n "$SERVER_IP" ]; then WEB="http://$SERVER_IP"; ADMIN="http://$SERVER_IP/admin/"; fi
if [ -n "$ADMIN_PASSWORD" ]; then
  LOGIN="admin / $ADMIN_PASSWORD   (guárdala; está en el .env, DJANGO_SUPERUSER_PASSWORD)"
elif [ -f .env ] && grep -q "^DJANGO_SUPERUSER_PASSWORD=" .env; then
  LOGIN="el usuario y la contraseña de DJANGO_SUPERUSER_* en tu .env"
else
  LOGIN="admin / admin   (si ya había un administrador, el tuyo)"
fi
say "¡Listo!"
cat <<EOF
  Web:    $WEB
  Wiki:   $WEB/wiki
  Admin:  $ADMIN  →  $LOGIN

  En segundo plano, sin que hagas nada:
  · se calculan las huellas del escáner (un buen rato la primera vez),
  · y cada día se ponen al día las cartas, la ban list y los precios.
EOF
if [ -n "$SERVER_IP" ]; then
  cat <<EOF

  Para terminar el servidor (necesita sudo; ver la wiki, «Instalación paso a paso»):
  · copias de seguridad diarias:
      make backups
  · instala $WEB/ca.crt en cada móvil para usar la cámara por HTTPS.
EOF
fi
