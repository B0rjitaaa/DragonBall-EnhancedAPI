# Instalación paso a paso

Instalar DragonBall EnhancedAPI en tu ordenador es **bajar el código y arrancarlo**. No hay nada que configurar ni copiar: la rama **`main`** del repositorio trae todo lo necesario.
- el código;
- el **catálogo completo de cartas**;
- los **precios** de todas ellas, con su historial;
- la ban list, la errata, las Q&A y las keyword skills;
- unos **valores por defecto** (`.env.defaults`) con los que todo funciona sin crear ningún fichero.

Al arrancar por primera vez, todo se prepara solo en menos de un minuto:
- se importan el catálogo y los precios;
- se crea el usuario del admin (**admin / admin**);
- el escáner empieza a calcular sus huellas en segundo plano.

Hay dos caminos:

- **[A. En tu ordenador](#a-instalacion-en-tu-ordenador)**: `docker compose up -d` y listo.
- **[B. En un servidor de casa](#b-instalacion-en-un-servidor-de-casa)**, para usarla a diario desde cualquier dispositivo de la red: `make install SERVER=<ip>` y las copias de seguridad.
- **[Extras](#extras-opcionales)**: copias fuera del servidor y vigilancia de caídas, con otro equipo de casa o con servicios externos.

Al final tienes la lista de [todo lo que tiene que estar en marcha](servicios.md) y cómo comprobarlo.

## Requisitos

| Qué | Para qué | Cómo comprobarlo |
|---|---|---|
| **Docker** con **Docker Compose v2.24 o posterior** | Ejecuta todos los servicios. En el Mac o Windows: Docker Desktop, abierto. En Linux: Docker Engine + el plugin compose. | `docker compose version` |
| **Git** | Bajar el código y actualizarlo. | `git --version` |
| **make** (opcional) | Atajos como `make up` o `make install`. Viene en macOS y Linux. | `make --version` |
| **4 GB de RAM** libres | Postgres, Redis, Django, dos workers y la web. | — |
| **~6 GB de disco** | Imágenes de Docker, base de datos e imágenes de las cartas. | `df -h` |
| **Internet** | Construir las imágenes la primera vez y, después, las actualizaciones diarias. | — |

Los puertos que se usan en el equipo son:

| Puerto | Qué |
|---|---|
| **5173** | La web |
| **8000** | La API y el admin (en local) |
| **5432** | Postgres |
| **80 / 443** | La web en un servidor (HTTP / HTTPS) |

---

## A. Instalación en tu ordenador

### Paso 1. Bajar el código

```bash
git clone https://github.com/B0rjitaaa/DragonBall-EnhancedAPI.git
cd DragonBall-EnhancedAPI
```

Se baja la rama **`main`**, la estable, que es la que se instala.

### Paso 2. Arrancar

```bash
docker compose up -d
```

La primera vez tarda unos minutos, porque construye las imágenes. Después, **todo ocurre solo**:

| Qué | Cómo |
|---|---|
| **Configuración** | Sin `.env`, se usan los valores de `.env.defaults`, pensados para tu ordenador. |
| **Base de datos** | Se crean las tablas y se cargan la ban list, la errata, las Q&A y las keyword skills. |
| **Catálogo** | Se importan las ~9.000 cartas de `data/seed/cartas_dbs.json.gz`, en segundos. |
| **Precios** | Se importan de `data/seed/precios_dbs.json.gz`: productos de Cardmarket y TCGplayer, emparejamientos, precios revisados a mano e historial. |
| **Administrador** | Se crea el usuario **`admin`** con contraseña **`admin`**, si no había ninguno. |
| **Escáner** | El `scanner_worker` calcula las huellas de todas las cartas en segundo plano. Descarga las imágenes oficiales, así que tarda un buen rato la primera vez. Cada carta se reconoce en cuanto tiene su huella. |
| **Cada día** | Se ponen al día solas las cartas nuevas, la ban list y los precios. |

> [!TIP]
> **Mejor aún: `make install`.** Hace lo mismo que `docker compose up -d`, pero además comprueba Docker, espera a que todo esté listo y te enseña un resumen: cuántas cartas y precios hay, las direcciones y el usuario.

### Paso 3. Entrar

| Qué | Dónde | Qué debes ver |
|---|---|---|
| La web | http://localhost:5173 | El buscador con cartas, y su precio al abrir una |
| La wiki | http://localhost:5173/wiki | Esta guía |
| El admin | http://localhost:8000/admin/ | Entra con **admin / admin** |
| La salud | http://localhost:8000/api/health/ | `"status": "ok"`. Justo tras instalar puede salir `degraded` hasta el primer sync y la primera copia. |
| La API | http://localhost:8000/api/docs/ | La documentación Swagger |

> [!WARNING]
> `admin / admin` está bien para tu ordenador. **Si otras personas pueden entrar** en ese equipo, cámbiala en el admin (arriba a la derecha → «Change password», cambiar contraseña). En un servidor, el instalador ya pone una contraseña aleatoria (paso B.3).

> [!TIP]
> **El día a día en local:**
> - **Parar:** `docker compose down` (o `make down`). Los datos se conservan.
> - **Volver a arrancar:** `docker compose up -d` (o `make up`).
> - **Ver los logs:** `make logs`.
> - **Abrir una consola de Django:** `make shell`.
> - **Abrir una consola de Postgres:** `make psql`.
> - **Pasar los tests:** `make test`.
>
> El código se recarga solo al guardar, salvo los workers de Celery: `docker compose restart celery_worker scanner_worker celery_beat`.

### Cambiar la configuración (opcional)

No hace falta para usarla. Si quieres cambiar algo, crea un fichero **`.env`** con **solo lo que cambie**: manda sobre `.env.defaults`. Después aplícalo con `docker compose up -d`. Tienes todas las opciones comentadas en `.env.example`.

| Valor por defecto (`.env.defaults`) | Qué es |
|---|---|
| `DJANGO_SECRET_KEY=dev-insecure-solo-para-local` | Clave de Django. En un servidor, una aleatoria. |
| `DJANGO_DEBUG=1` | Modo desarrollo. En un servidor, `0`. |
| `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,backend` | Direcciones desde las que se puede entrar. |
| `DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:5173,…` | Orígenes desde los que se puede guardar con una sesión del admin abierta. En un servidor, sus direcciones (lo pone el instalador). |
| `DJANGO_SUPERUSER_USERNAME=admin` · `DJANGO_SUPERUSER_PASSWORD=admin` | El administrador que se crea solo si no hay ninguno. |
| `POSTGRES_DB/USER/PASSWORD=dbs` · `POSTGRES_HOST=db` | La base de datos del compose. |
| `REDIS_URL=redis://redis:6379` | Redis del compose. |
| `BANDAI_REQUEST_DELAY=0.25` · `BANDAI_WORKERS=4` | Ritmo de descarga de Bandai. |
| `MATCH_MIN_CONFIDENCE=0.45` · `AUTO_ADD_MIN_CONFIDENCE=0.65` | Umbrales del escáner. |
| `SCAN_RETENTION_HOURS=24` · `SCAN_PHOTOS_MAX_MB=2048` | Cuánto duran las fotos de los escaneos. |

Opciones que solo van en `.env`:
- **Telegram:** `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`, para recibir avisos.
- **Webcam USB:** `COMPOSE_PROFILES=camera` y `CAMERA_*`, si hay webcam.
- **Puertos de un servidor:** `HTTP_PORT` y `HTTPS_PORT`.

### Los datos que trae el repositorio

| Fichero | Qué es | Tamaño |
|---|---|---|
| `data/seed/cartas_dbs.json.gz` | El catálogo completo: los registros originales de Bandai y las impresiones propias. | ~1 MB |
| `data/seed/precios_dbs.json.gz` | Los precios: productos y emparejamientos de Cardmarket y TCGplayer, **las elecciones y precios a mano** de la revisión, el cambio del dólar, el precio de cada carta y su historial. | ~1 MB |
| `backend/cards/data/*_snapshot.json` | Ban list, errata, Q&A y keyword skills (las cargan las migraciones). | — |

**Solo se importan con la base de datos vacía**, es decir, en la primera instalación. Después, tu instalación se pone al día sola cada día y los datos del repositorio ya no se usan. Si en `data/` hay un volcado más reciente (`cartas_dbs.json` o `precios_dbs.json`, como el que rehace el servidor cada día), se usa ese en lugar del del repositorio.

**Para poner al día los datos del repositorio** (lo hace quien mantiene el proyecto, mejor desde el servidor):

```bash
make seed      # rehace data/seed/cartas_dbs.json.gz y data/seed/precios_dbs.json.gz
git add data/seed && git commit -m "Datos: catálogo y precios al día"
```

### Los servicios que se levantan

| Servicio | Qué es | Puerto |
|---|---|---|
| `db` | PostgreSQL 16 | 5432 |
| `redis` | Redis 7 | — |
| `backend` | Django (API y admin) | 8000 |
| `celery_worker` | Tareas de fondo | — |
| `scanner_worker` | Reconocimiento del escáner | — |
| `celery_beat` | Lanza las tareas programadas | — |
| `frontend` | La web (Vite) | 5173 |
| `camera` | Webcam USB, **solo** con `COMPOSE_PROFILES=camera` | — |

Lo que hace cada uno, y cómo comprobarlo, está en [Qué tiene que estar en marcha](servicios.md).

---

## B. Instalación en un servidor de casa

Para tenerla siempre encendida y usarla desde el móvil y cualquier ordenador de la red:
- la web en los puertos 80 y 443, con nginx;
- el backend con gunicorn;
- HTTPS para la cámara del móvil;
- copias de seguridad diarias;
- avisos por Telegram;
- actualización con un `git pull`.

Se parte de un Linux con Docker (Ubuntu, Debian…). En los ejemplos, el servidor es **`192.168.1.50`** y su usuario es **`usuario`**. Cámbialos por los tuyos.

### Paso 1. Preparar el equipo

```bash
# Docker, el plugin compose, git y make (Debian/Ubuntu)
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git make
sudo usermod -aG docker $USER     # para usar docker sin sudo (cierra sesión y vuelve a entrar)
```

> [!IMPORTANT]
> **Dale al servidor una IP fija**: resérvala en el router para que no cambie. De ella dependen el certificado HTTPS, los enlaces y el vigilante. Mejor si va **por cable**: algunos adaptadores Wi-Fi USB pierden la red y dejan el equipo inaccesible.

### Paso 2. Bajar el código

```bash
mkdir -p ~/Development && cd ~/Development
git clone https://github.com/B0rjitaaa/DragonBall-EnhancedAPI.git
cd DragonBall-EnhancedAPI
```

El servidor trabaja siempre sobre la rama **`main`**, la que se baja por defecto.

### Paso 3. Instalar en modo servidor

```bash
make install SERVER=192.168.1.50
```

Hace lo mismo que en tu ordenador y, además:
- **Crea el `.env` de producción**, con permisos `600`:
  - claves aleatorias para Django, Postgres y el **administrador**. La contraseña del admin se muestra al terminar: guárdala;
  - `COMPOSE_FILE` con `docker-compose.prod.yml`, para nginx y gunicorn;
  - `DJANGO_DEBUG=0`;
  - la IP en `DJANGO_ALLOWED_HOSTS` y `DJANGO_CSRF_TRUSTED_ORIGINS`;
  - las carpetas de copias (`BACKUP_DIR_HOST`, `BACKUP_STATUS_FILE`), y crea `~/backups/dbs/request`.
- **Crea el certificado HTTPS** para la cámara del móvil (`scripts/local-https.sh`) y activa el puerto 443.
- **Activa la actualización automática:** cada `git pull` en `main` despliega solo.

Al terminar, abre `http://192.168.1.50/` y entra en `http://192.168.1.50/admin/` con `admin` y la contraseña que te ha mostrado.

### Paso 4 (opcional). Avisos por Telegram

1. Crea un bot con **@BotFather** en Telegram y apunta su token.
2. Escríbele un mensaje y apunta el id del chat.
3. Añade al `.env`:

   ```bash
   TELEGRAM_BOT_TOKEN=<token del bot>
   TELEGRAM_CHAT_ID=<id del chat>
   ```

4. Aplícalo con `docker compose up -d`.

Qué avisos llegan: [Tareas programadas y avisos](tareas-programadas.md).

### Paso 5. El certificado en cada móvil

Para que el móvil confíe en el certificado del paso 3, **en cada móvil**:
1. Abre `http://192.168.1.50/ca.crt` y descarga el perfil.
2. **iPhone:**
   1. Ajustes → *Perfil descargado* → Instalar.
   2. Ajustes → General → Información → **Confianza de certificados** → actívalo.
3. **Android:** Ajustes → Seguridad → Instalar certificado (CA).

Comprueba que `https://192.168.1.50/scan` abre la cámara. Más en [Usar el escáner](escaner.md).

### Paso 6. Copias de seguridad diarias

Las copias no las hace Docker sino **systemd**, en el propio servidor. Para instalarlas:

```bash
make backups      # pide la contraseña de sudo
```

Rellena las plantillas de `scripts/systemd/` con tu usuario y la carpeta del proyecto, y activa:
- **la copia diaria a las 03:30.** Si el equipo estaba apagado a esa hora, se hace al encenderlo;
- **el botón «Back up now»** (hacer copia ahora) del admin.

Prueba una copia a mano y mira cómo acaba:

```bash
sudo systemctl start dbs-backup.service
journalctl -t dbs-backup -n 30
ls ~/backups/dbs/daily/
```

En el admin, **Backups** (copias de seguridad) debe decir «✅ Last backup succeeded» (última copia correcta). Más en [Copias de seguridad](copias-de-seguridad.md).

### Paso 7. Repaso final

Recorre la lista de [Qué tiene que estar en marcha](servicios.md):
- los 7 contenedores;
- las 2 unidades de systemd;
- la salud en `ok`.

Con esto el servidor está completo. Lo que sigue es opcional.

---

## Extras (opcionales)

Nada de esto hace falta para usar la web, pero cubre dos riesgos que tiene cualquier servidor de casa:
- **que se rompa el disco del servidor** y te quedes sin copias, porque estaban en el mismo disco;
- **que el servidor se caiga** y no te enteres, porque es él quien manda los avisos.

Para cada riesgo hay dos opciones: **otro equipo de casa** si tienes uno (una Raspberry Pi, un NAS, otro ordenador siempre encendido) o un **servicio externo** si no.

| Riesgo | Con otro equipo de casa | Con un servicio externo |
|---|---|---|
| Perder las copias | [Réplica por rsync](#copia-fuera-del-servidor-en-otro-equipo-de-casa) | [Copia en la nube con rclone](#copia-fuera-del-servidor-en-la-nube-rclone) o [en un VPS](#copia-fuera-del-servidor-en-un-vps) |
| No enterarte de una caída | [Vigilante `watchdog.py`](#vigilancia-con-otro-equipo-de-casa) | [Latido a Healthchecks.io](#vigilancia-con-un-servicio-externo-healthchecksio) |

Las copias de fuera se configuran en `~/.config/dbs-backup.env` del servidor y se puede usar más de una a la vez. En el admin, **Backups → «Off-server copy»** (copia fuera del servidor) dice si la última fue bien.

### Copia fuera del servidor: en otro equipo de casa

Se replican las copias por **rsync** en otro equipo de la red (en el ejemplo, `192.168.1.60` con el usuario `usuario`). Se usa una clave SSH que **solo puede escribir copias** en una carpeta.

1. **En el servidor**, crea la clave:

   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/dbs_backup_ed25519 -N ""
   cat ~/.ssh/dbs_backup_ed25519.pub
   ```

2. **En el otro equipo**, autoriza esa clave solo para escribir en `~/backups-dbs`. Usa `rrsync`, que viene con rsync (`sudo apt install rsync`):

   ```bash
   mkdir -p ~/backups-dbs
   # Una línea en ~/.ssh/authorized_keys:
   command="/usr/bin/rrsync -wo /home/usuario/backups-dbs",restrict ssh-ed25519 AAAA…(la clave pública)
   ```

3. **En el servidor**, añade a `~/.config/dbs-backup.env` el destino. Termina en `:` porque `rrsync` ya fija la carpeta:

   ```bash
   BACKUP_REMOTE=usuario@192.168.1.60:
   ```

4. Lanza una copia (`sudo systemctl start dbs-backup.service`). En el admin debe salir «Off-server copy: ✅ copied».

> [!WARNING]
> La carpeta de destino es una **réplica exacta**: lo que no esté en el servidor se borra de ella. No guardes otros ficheros ahí.

### Copia fuera del servidor: en la nube (rclone)

**rclone** copia las copias a casi cualquier almacenamiento en la nube:
- **Backblaze B2**: 10 GB gratis, recomendado;
- **Google Drive**, **Dropbox** u **OneDrive**;
- **Amazon S3** y compatibles (Cloudflare R2, Wasabi…).

Con 7 copias diarias y 4 semanales se usan unos pocos cientos de MB.

1. **Instala rclone** en el servidor:

   ```bash
   sudo apt install -y rclone          # o la última versión: curl https://rclone.org/install.sh | sudo bash
   ```

2. **Crea el «remoto»** con el asistente. Ejemplo con Backblaze B2:
   1. En backblaze.com, crea un *bucket* privado, por ejemplo `mis-copias-dbs`, y una *Application Key* con acceso solo a ese bucket.
   2. En el servidor:

      ```bash
      rclone config
      # n (nuevo) → nombre: b2 → tipo: b2 → account: el keyID → key: la applicationKey → resto por defecto
      ```

   3. Comprueba que funciona: `rclone lsd b2:` debe listar el bucket.

   Para **Google Drive** o **Dropbox** el asistente abre el navegador para dar permiso. Si el servidor no tiene pantalla, rclone explica cómo autorizarlo desde otro ordenador (`rclone authorize`).

3. **(Recomendado) Cifra las copias** antes de subirlas. En `rclone config` crea otro remoto de tipo **`crypt`** que apunte a `b2:mis-copias-dbs/dbs`, con una contraseña que **guardes fuera del servidor**: sin ella las copias no se pueden leer.
4. **En el servidor**, añade a `~/.config/dbs-backup.env`:

   ```bash
   BACKUP_RCLONE=b2:mis-copias-dbs/dbs        # o el remoto cifrado, p. ej. copias-cifradas:
   ```

5. Lanza una copia (`sudo systemctl start dbs-backup.service`) y comprueba que llega: `rclone ls b2:mis-copias-dbs/dbs | head`. En el admin: «Off-server copy: ✅ copied».

**Para recuperar una copia** desde la nube, en cualquier equipo con rclone y el mismo remoto:

```bash
rclone copy b2:mis-copias-dbs/dbs/daily/2026-10-29_0330 ./restaurar/
```

Después, restaura como se explica en [Copias de seguridad](copias-de-seguridad.md#restaurar).

### Copia fuera del servidor: en un VPS

Si tienes un **servidor en Internet** con SSH (un VPS de Hetzner, OVH, DigitalOcean…), funciona igual que [con otro equipo de casa](#copia-fuera-del-servidor-en-otro-equipo-de-casa): la clave limitada con `rrsync` en el VPS y, en el servidor:

```bash
BACKUP_REMOTE=usuario@mi-vps.example.com:
```

### Vigilancia: con un servicio externo (Healthchecks.io)

**Healthchecks.io** es gratis hasta 20 comprobaciones y avisa por **Telegram**, correo y otros canales. No hace falta abrir puertos ni exponer el servidor a Internet.

Funciona como un «hombre muerto»: cada 5 minutos el servidor le manda un **latido**. Te avisa en dos casos:
- **el latido deja de llegar**: servidor apagado, sin Internet, o Celery o Redis caídos;
- **llega marcado como fallo**: algo crítico del servidor ha caído (base de datos, workers…).

1. Crea una cuenta en **healthchecks.io** y pulsa **Add Check**:
   - **Name:** DragonBall EnhancedAPI;
   - **Period:** 5 minutos;
   - **Grace time:** 10 minutos, para no avisar por un reinicio.
2. En **Integrations**, añade **Telegram**: el asistente te da un bot al que escribir. También puedes usar el correo.
3. Copia la **Ping URL** del check (algo como `https://hc-ping.com/1234abcd-…`) y añádela al `.env` del servidor:

   ```bash
   HEALTHCHECKS_URL=https://hc-ping.com/1234abcd-…
   ```

4. Aplícalo con `docker compose up -d`. En unos minutos, el check en healthchecks.io pasa a **Up**.

Para probarlo, para el worker un cuarto de hora (`docker compose stop celery_worker`): te llegará el aviso. Después vuelve a arrancarlo con `docker compose start celery_worker`.

> [!TIP]
> Cualquier servicio compatible con «ping URLs» vale igual, por ejemplo **Better Stack (Heartbeats)** o **Cronitor**. El servidor manda un `POST` a la URL cuando todo va bien, y a `<URL>/fail` cuando algo crítico falla.

### Vigilancia: con otro equipo de casa

El **vigilante** (`scripts/watchdog.py`) corre en otro equipo de la red. Cada 5 minutos consulta la salud del servidor y avisa por Telegram si no responde. Solo usa Python, que ya viene en Linux:

```bash
# En el otro equipo
mkdir -p ~/dbs-watchdog && cd ~/dbs-watchdog
curl -fsSLO https://raw.githubusercontent.com/B0rjitaaa/DragonBall-EnhancedAPI/main/scripts/watchdog.py
cat > watchdog.env <<'EOF'
HEALTH_URL=http://192.168.1.50/api/health/
TELEGRAM_BOT_TOKEN=<token del bot>
TELEGRAM_CHAT_ID=<id del chat>
EOF
chmod 600 watchdog.env
python3 watchdog.py watchdog.env --test     # debe llegar «👀 Watchdog active»
crontab -e
# */5 * * * * /usr/bin/python3 /home/usuario/dbs-watchdog/watchdog.py /home/usuario/dbs-watchdog/watchdog.env >> /home/usuario/dbs-watchdog/watchdog.log 2>&1
```

Para actualizarlo, vuelve a lanzar el `curl`. Más en [Tareas programadas y avisos](tareas-programadas.md#con-otro-equipo-de-casa-el-vigilante).

### Webcam USB del escáner

Si el servidor tiene una webcam para escanear sin móvil, añade al `.env`:

```bash
COMPOSE_PROFILES=camera
CAMERA_URL=http://camera:8080
CAMERA_DEVICE=/dev/video0
```

Y aplícalo con `docker compose up -d`. En el escáner aparecerá «Scanner webcam» (webcam del escáner).

### ¿Y montar el servidor entero fuera de casa?

Se puede instalar todo en un **VPS** con los mismos pasos de esta guía, usando su IP o su dominio en `make install SERVER=`. Pero hoy la web **no tiene cuentas de usuario**: cualquiera que llegue a ella puede ver y cambiar tu colección. Hasta que las tenga, si la pones en Internet protégela delante, por ejemplo con **Cloudflare Tunnel + Cloudflare Access** (inicio de sesión con tu correo) o con una VPN como **Tailscale**.

---

## Actualizar una instalación

| Dónde | Cómo |
|---|---|
| En tu ordenador | `git pull` y `docker compose up -d --build`. Las migraciones se aplican solas al arrancar. |
| En el servidor | `git pull` y nada más: el despliegue se lanza solo. Si no, `make deploy`. |

Si cambias el **`.env`** o los **volúmenes** de `docker-compose*.yml`, ejecuta además `docker compose up -d`.

## Desinstalar

```bash
docker compose down        # para todo; los datos se quedan en los volúmenes
docker compose down -v     # para todo y BORRA la base de datos, Redis y los ficheros (¡irreversible!)
```

En un servidor, además:

```bash
sudo systemctl disable --now dbs-backup.timer dbs-backup-request.path
sudo rm /etc/systemd/system/dbs-backup*
```

## Problemas al instalar

| Síntoma | Causa probable | Solución |
|---|---|---|
| `port is already allocated` | Otro programa usa el 5173, 8000, 5432 u 80 | Páralo, o cambia el puerto en `docker-compose.yml` o en el `.env` (`HTTP_PORT`). |
| `env_file … required` o un error sobre `path` | Docker Compose demasiado antiguo | Actualízalo a la versión 2.24 o posterior. |
| El backend se reinicia en bucle con «Postgres is not responding» | La base no arranca | `docker compose logs db`. Suele ser falta de disco o un volumen de otra versión de Postgres. |
| La web carga pero sin cartas | No se importó el catálogo | `docker compose logs backend \| grep -i import`. Si falta `data/seed/`, `git pull`; si no, `make sync` y espera. |
| No puedo entrar en el admin con admin / admin | Ya había otro administrador (instalación anterior), o es un servidor | Usa el tuyo, o la contraseña de `DJANGO_SUPERUSER_PASSWORD` en el `.env`. Para crear otro: `make superuser`. |
| Bandai responde 403 o 429 en los logs | Demasiadas peticiones | Se pausa sola y reintenta. Si se repite, sube `BANDAI_REQUEST_DELAY` en el `.env`. |
| El escáner dice «No matches: have the fingerprints been computed?» (sin coincidencias) | Las huellas aún se están calculando | Espera: se calculan solas tras instalar (`docker compose logs -f scanner_worker`). |
| El admin no tiene estilos | Faltan los estáticos | `docker compose restart backend` (los genera al arrancar). |
| Error «CSRF … Origin checking failed» al guardar | Entras por una dirección que no está en `DJANGO_CSRF_TRUSTED_ORIGINS` | Añádela al `.env` (separadas por comas) y aplica con `docker compose up -d`. |
| La cámara del móvil no abre | Página sin HTTPS o certificado no instalado | Pasos 3 y 5 (B). |
