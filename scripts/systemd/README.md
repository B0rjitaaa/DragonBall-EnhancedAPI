# Copias de seguridad (systemd, en el servidor)

Plantillas: `@USER@`, `@HOME@` y `@REPO@` se rellenan al instalar con el usuario y la carpeta del proyecto.

- `dbs-backup.service`: lanza `scripts/backup.sh` como ese usuario.
- `dbs-backup.timer`: a diario a las 03:30 (si el equipo estaba apagado, al encenderlo).
- `dbs-backup-request.path`: cuando el admin pide una copia («Hacer copia ahora»).

Instalar o actualizar (pide la contraseña de sudo):

```sh
make backups        # = bash scripts/systemd/install.sh
```
