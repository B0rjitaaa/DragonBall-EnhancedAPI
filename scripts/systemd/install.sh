#!/usr/bin/env bash
# Instala las copias de seguridad diarias (systemd) para el usuario y la carpeta actuales: rellena las
# plantillas (@USER@, @HOME@, @REPO@) y las activa. Uso: make backups (pide la contraseña de sudo).
set -euo pipefail
cd "$(dirname "$0")"
REPO="$(cd ../.. && pwd)"
USER_NAME="$(id -un)"
HOME_DIR="$HOME"
mkdir -p "$HOME_DIR/backups/dbs/request"
for unit in dbs-backup.service dbs-backup.timer dbs-backup-request.path; do
  sed -e "s#@USER@#$USER_NAME#g" -e "s#@HOME@#$HOME_DIR#g" -e "s#@REPO@#$REPO#g" "$unit" \
    | sudo tee "/etc/systemd/system/$unit" >/dev/null
done
sudo systemctl daemon-reload
sudo systemctl enable --now dbs-backup.timer dbs-backup-request.path
echo "✔ Copias diarias a las 03:30 para $USER_NAME (copias en $HOME_DIR/backups/dbs)"
systemctl list-timers dbs-backup.timer --no-pager | head -3
