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
  if [ -n "$IMPORT_ON_START" ]; then
    python manage.py import_cards "$IMPORT_ON_START" --if-empty
  fi
fi

exec "$@"
