# Copias de seguridad

Todos los datos (catálogo, colección, mazos, partidas, precios, escaneos…) viven en la base de datos del servidor. **Cada noche se hace una copia** automáticamente y, si lo configuras, se lleva también fuera del servidor (otro equipo, la nube o un VPS). Desde el admin puedes ver su estado, hacer una copia al momento y descargarla.

![La página Backups (copias de seguridad) del admin](../img/admin-copias.jpg)

## La página del admin

En el admin: **Backups** (copias de seguridad; `/admin/backups/backup/`).

### Estado

Arriba se ve cómo fue la última copia:
- **⏳ Backup in progress** (copia en curso): suele tardar unos 15 minutos;
- **⏳ Backup requested** (copia pedida): empezará en unos segundos;
- **✅ Last backup succeeded** (última copia correcta);
- **❌ The last backup failed** (la última copia falló), con el mensaje de error: en qué paso falló, qué comando y sus últimas líneas;
- **No backups yet** (aún no hay ninguna copia).

Debajo, la línea **Off-server copy:** (copia fuera del servidor) dice si la última copia externa fue bien (**✅ copied**), falló (**❌ failed**) o no está configurada (**not configured**).

Mientras hay una copia en curso, la página se recarga sola cada 15 segundos.

### Hacer copia ahora

El botón **«Back up now»** (hacer copia ahora) lanza una copia en el momento. El mensaje dice «Backup requested: it will start in a few seconds and takes about 15 minutes.»

> [!TIP]
> Haz una copia a mano **antes de cambios gordos**: importar un CSV grande, reorganizar ubicaciones o desplegar una versión con cambios en la base de datos.

### Descargar

Las copias se agrupan en **Daily** (diarias), **Weekly** (semanales) y **Other** (otras carpetas), con su fecha. Se pueden descargar los ficheros `.dump` de la base de datos.

## Qué se copia

| Qué | Cómo |
|---|---|
| **Base de datos** | `pg_dump` en formato comprimido (`.dump`), y se comprueba que se puede leer. |
| **Ficheros** (volumen `media`) | Un `.tgz` con las imágenes de las [impresiones propias](datos-y-sincronizacion.md#impresiones-propias). Se comprueba que el `.tgz` se puede abrir. |
| **No se copian** | Las fotos de los escaneos (se borran a las 24 h de todos modos), Redis ni la caché de imágenes oficiales (se vuelve a descargar). |

## Cuándo y cuántas

- **Diaria:** a las **03:30**. La lanza un temporizador de systemd en el servidor, fuera de Docker. Si el equipo estaba apagado a esa hora, la copia se hace al encenderlo.
- **Semanal:** los **domingos** la copia del día se guarda además como semanal.
- **Retención:** se guardan **7 diarias** y **4 semanales**; las más viejas se borran solas.
- **Copia fuera del servidor (opcional):** después de cada copia, todo se puede llevar también:
  - a **otro equipo de casa** o a un **VPS**, por rsync (`BACKUP_REMOTE`);
  - a **la nube** con rclone (`BACKUP_RCLONE`): Backblaze B2, Google Drive, Dropbox, S3…

  Si falla, la copia local sigue valiendo y se apunta el fallo. Cómo configurarla: [Instalación → Extras](instalacion.md#extras-opcionales).

## Si una copia falla

No hace falta mirar la página a diario:
- La comprobación de salud marca la copia como fallida si la última **falló**, tiene **más de 30 horas** o **no se replicó**.
- Te llega un **aviso por Telegram** (🟡, silencioso). Ver [Tareas programadas y avisos](tareas-programadas.md).

En el servidor, los detalles están en el registro del sistema:

```bash
journalctl -t dbs-backup -n 50
```

## Restaurar

> [!CAUTION]
> Restaurar **sustituye** la base de datos actual por la de la copia. Todo lo hecho después de la copia se pierde. Haz antes una copia de lo actual.

En el servidor, desde la carpeta del proyecto:

```bash
# 1. Base de datos (sustituye el contenido actual)
docker compose exec -T db pg_restore --clean -U <usuario> -d <base> < ~/backups/dbs/daily/<fecha>/DragonBall-EnhancedAPI.dump

# 2. Ficheros (imágenes de impresiones propias)
docker run --rm -v dragonball-enhancedapi_media:/data -i alpine tar xzf - -C /data < copia.tgz

# 3. Reiniciar los servicios
docker compose restart backend celery_worker celery_beat scanner_worker
```

El usuario y el nombre de la base están en el `.env` del servidor (`POSTGRES_USER`, `POSTGRES_DB`).

## Instalación (una vez, en el servidor)

```bash
make backups      # pide la contraseña de sudo
```

Instala y activa las unidades de `scripts/systemd/`, rellenando sus plantillas con tu usuario y la carpeta del proyecto:
- `dbs-backup.service`: la copia;
- `dbs-backup.timer`: todos los días a las 03:30;
- `dbs-backup-request.path`: lanza la copia cuando el admin crea el fichero `~/backups/dbs/request/now`. Así funciona el botón «Back up now».

Si cambian esos ficheros, vuelve a lanzar `make backups`.

`scripts/backup.sh` se configura con variables de entorno o con `~/.config/dbs-backup.env`:

| Variable | Valor por defecto |
|---|---|
| `BACKUP_DIR` | `~/backups/dbs` |
| `KEEP_DAILY` | 7 |
| `KEEP_WEEKLY` | 4 |
| `BACKUP_REMOTE` | vacío: sin copia por rsync (otro equipo o VPS) |
| `BACKUP_SSH_KEY` | `~/.ssh/dbs_backup_ed25519` |
| `BACKUP_RCLONE` | vacío: sin copia en la nube (p. ej. `b2:mis-copias-dbs/dbs`) |

> [!WARNING]
> Los destinos de fuera son una **réplica exacta**: lo que no esté en el servidor se borra de ellos. No guardes otros ficheros ahí.
