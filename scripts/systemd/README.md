# Copias de seguridad (systemd, en el servidor)

- `dbs-backup.service`: lanza `scripts/backup.sh` como `pc-mint`.
- `dbs-backup.timer`: a diario a las 03:30.
- `dbs-backup-request.path`: cuando el admin pide una copia («Hacer copia ahora»).

Instalar o actualizar:

```sh
sudo cp scripts/systemd/dbs-backup.* scripts/systemd/dbs-backup-request.path /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now dbs-backup.timer dbs-backup-request.path
```
