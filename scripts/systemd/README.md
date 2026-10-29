# Backups (systemd, on the server)

Templates: `@USER@`, `@HOME@` and `@REPO@` are filled in at install time with the user and the project folder.

- `dbs-backup.service`: runs `scripts/backup.sh` as that user.
- `dbs-backup.timer`: daily at 03:30 (if the machine was off, when it is turned on).
- `dbs-backup-request.path`: when a backup is requested from the admin ("Back up now").

Install or update (asks for the sudo password):

```sh
make backups        # = bash scripts/systemd/install.sh
```
