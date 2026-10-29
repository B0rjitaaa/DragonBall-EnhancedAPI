#!/bin/sh
set -e

# Esperar a Postgres
python - <<'PY'
import os, time, psycopg
for i in range(60):
    try:
        psycopg.connect(
            host=os.environ.get("POSTGRES_HOST", "db"), port=os.environ.get("POSTGRES_PORT", "5432"),
            dbname=os.environ["POSTGRES_DB"], user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"], connect_timeout=3,
        ).close()
        break
    except psycopg.OperationalError:
        print("Esperando a Postgres...", flush=True)
        time.sleep(2)
else:
    raise SystemExit("Postgres no responde")
PY

if [ "$RUN_MIGRATIONS" = "1" ]; then
  python manage.py migrate --noinput
  # Estáticos del admin (los sirve WhiteNoise también con DEBUG desactivado). Se generan al
  # arrancar porque el código se monta como volumen y taparía los de la imagen.
  python manage.py collectstatic --noinput -v 0
  # Base vacía: el catálogo y los precios, del volcado más reciente que haya: el del servidor
  # (data/*.json) o el que va en el repositorio (data/seed/*.json.gz).
  CARDS_FILE="${IMPORT_ON_START-/data/cartas_dbs.json}"
  [ -f "$CARDS_FILE" ] || CARDS_FILE=/data/seed/cartas_dbs.json.gz
  python manage.py import_cards "$CARDS_FILE" --if-empty
  python manage.py import_prices --if-empty || echo "No se pudieron importar los precios"
  # Sin ningún administrador (instalación nueva): admin / admin, o lo de DJANGO_SUPERUSER_*.
  python manage.py ensure_admin
fi

exec "$@"
