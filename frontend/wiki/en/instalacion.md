# Step-by-step installation

Installing DragonBall EnhancedAPI on your computer means **getting the code and starting it**. There is nothing to configure or copy: the repository's **`main`** branch brings everything you need.
- the code;
- the **complete card catalog**;
- the **prices** of all of them, with their history;
- the ban list, the errata, the Q&A and the keyword skills;
- some **default values** (`.env.defaults`) that make everything work without creating any file.

The first time it starts, everything gets ready by itself in under a minute:
- the catalog and the prices are imported;
- the admin user is created (**admin / admin**);
- the scanner starts computing its fingerprints in the background.

There are two paths:

- **[A. On your computer](#a-installing-on-your-computer)**: `docker compose up -d` and you're done.
- **[B. On a home server](#b-installing-on-a-home-server)**, to use it every day from any device on your network: `make install SERVER=<ip>` and the backups.
- **[Extras](#extras-optional)**: off-server backups and outage monitoring, with another machine at home or with external services.

At the end you'll find the list of [everything that must be running](servicios.md) and how to check it.

## Requirements

| What | What for | How to check it |
|---|---|---|
| **Docker** with **Docker Compose v2.24 or later** | Runs all the services. On Mac or Windows: Docker Desktop, open. On Linux: Docker Engine + the compose plugin. | `docker compose version` |
| **Git** | Getting the code and updating it. | `git --version` |
| **make** (optional) | Shortcuts like `make up` or `make install`. Comes with macOS and Linux. | `make --version` |
| **4 GB of free RAM** | Postgres, Redis, Django, two workers and the web app. | — |
| **~6 GB of disk** | Docker images, the database and the card images. | `df -h` |
| **Internet** | Building the images the first time and, after that, the daily updates. | — |

The ports used on the machine are:

| Port | What |
|---|---|
| **5173** | The web app |
| **8000** | The API and the admin (locally) |
| **5432** | Postgres |
| **80 / 443** | The web app on a server (HTTP / HTTPS) |

---

## A. Installing on your computer

### Step 1. Get the code

```bash
git clone https://github.com/B0rjitaaa/DragonBall-EnhancedAPI.git
cd DragonBall-EnhancedAPI
```

This gets the **`main`** branch, the stable one, which is the one you install.

### Step 2. Start it

```bash
docker compose up -d
```

The first time takes a few minutes, because it builds the images. After that, **everything happens by itself**:

| What | How |
|---|---|
| **Configuration** | Without a `.env`, the values in `.env.defaults` are used, meant for your computer. |
| **Database** | The tables are created and the ban list, errata, Q&A and keyword skills are loaded. |
| **Catalog** | The ~9,000 cards in `data/seed/cartas_dbs.json.gz` are imported, in seconds. |
| **Prices** | Imported from `data/seed/precios_dbs.json.gz`: Cardmarket and TCGplayer products, matches, prices reviewed by hand and history. |
| **Administrator** | The user **`admin`** with password **`admin`** is created, if there wasn't one. |
| **Scanner** | The `scanner_worker` computes the fingerprints of every card in the background. It downloads the official images, so it takes quite a while the first time. Each card is recognized as soon as it has its fingerprint. |
| **Every day** | New cards, the ban list and prices update by themselves. |

> [!TIP]
> **Even better: `make install`.** It does the same as `docker compose up -d`, but it also checks Docker, waits until everything is ready and shows you a summary: how many cards and prices there are, the addresses and the user.

### Step 3. Open it

| What | Where | What you should see |
|---|---|---|
| The web app | http://localhost:5173 | Search with cards, and their price when you open one |
| The wiki | http://localhost:5173/wiki | This guide |
| The admin | http://localhost:8000/admin/ | Log in with **admin / admin** |
| Health | http://localhost:8000/api/health/ | `"status": "ok"`. Right after installing it may show `degraded` until the first sync and the first backup. |
| The API | http://localhost:8000/api/docs/ | The Swagger documentation |

> [!WARNING]
> `admin / admin` is fine for your computer. **If other people can use** that machine, change it in the admin (top right → **Change password**). On a server, the installer already sets a random password (step B.3).

> [!TIP]
> **Day to day, locally:**
> - **Stop:** `docker compose down` (or `make down`). Your data is kept.
> - **Start again:** `docker compose up -d` (or `make up`).
> - **See the logs:** `make logs`.
> - **Open a Django shell:** `make shell`.
> - **Open a Postgres shell:** `make psql`.
> - **Run the tests:** `make test`.
>
> The code reloads by itself when you save, except for the Celery workers: `docker compose restart celery_worker scanner_worker celery_beat`.

### Changing the configuration (optional)

You don't need this to use it. If you want to change something, create a **`.env`** file with **only what changes**: it overrides `.env.defaults`. Then apply it with `docker compose up -d`. All the options are commented in `.env.example`.

| Default value (`.env.defaults`) | What it is |
|---|---|
| `DJANGO_SECRET_KEY=dev-insecure-solo-para-local` | Django key. On a server, a random one. |
| `DJANGO_DEBUG=1` | Development mode. On a server, `0`. |
| `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,backend` | Addresses it can be reached from. |
| `DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:5173,…` | Origins that can save while an admin session is open. On a server, its addresses (the installer sets them). |
| `DJANGO_SUPERUSER_USERNAME=admin` · `DJANGO_SUPERUSER_PASSWORD=admin` | The administrator created only if there is none. |
| `POSTGRES_DB/USER/PASSWORD=dbs` · `POSTGRES_HOST=db` | The compose database. |
| `REDIS_URL=redis://redis:6379` | The compose Redis. |
| `BANDAI_REQUEST_DELAY=0.25` · `BANDAI_WORKERS=4` | Download pace from Bandai. |
| `MATCH_MIN_CONFIDENCE=0.45` · `AUTO_ADD_MIN_CONFIDENCE=0.65` | Scanner thresholds. |
| `SCAN_RETENTION_HOURS=24` · `SCAN_PHOTOS_MAX_MB=2048` | How long scan photos are kept. |

Options that only go in `.env`:
- **Telegram:** `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`, to receive alerts.
- **USB webcam:** `COMPOSE_PROFILES=camera` and `CAMERA_*`, if there is a webcam.
- **Server ports:** `HTTP_PORT` and `HTTPS_PORT`.

### The data included in the repository

| File | What it is | Size |
|---|---|---|
| `data/seed/cartas_dbs.json.gz` | The complete catalog: Bandai's original records and the own printings. | ~1 MB |
| `data/seed/precios_dbs.json.gz` | The prices: Cardmarket and TCGplayer products and matches, **the choices and prices set by hand** in the review, the dollar rate, each card's price and its history. | ~1 MB |
| `backend/cards/data/*_snapshot.json` | Ban list, errata, Q&A and keyword skills (loaded by the migrations). | — |

**They are only imported into an empty database**, that is, on the first installation. After that, your installation updates itself every day and the repository data is no longer used. If there is a more recent dump in `data/` (`cartas_dbs.json` or `precios_dbs.json`, like the one the server rebuilds every day), that one is used instead of the repository's.

**To update the repository data** (done by whoever maintains the project, preferably from the server):

```bash
make seed      # rebuilds data/seed/cartas_dbs.json.gz and data/seed/precios_dbs.json.gz
git add data/seed && git commit -m "Data: catalog and prices up to date"
```

### The services that start

| Service | What it is | Port |
|---|---|---|
| `db` | PostgreSQL 16 | 5432 |
| `redis` | Redis 7 | — |
| `backend` | Django (API and admin) | 8000 |
| `celery_worker` | Background tasks | — |
| `scanner_worker` | Scanner recognition | — |
| `celery_beat` | Launches the scheduled tasks | — |
| `frontend` | The web app (Vite) | 5173 |
| `camera` | USB webcam, **only** with `COMPOSE_PROFILES=camera` | — |

What each one does, and how to check it, is in [What must be running](servicios.md).

---

## B. Installing on a home server

To have it always on and use it from your phone and any computer on the network:
- the web app on ports 80 and 443, with nginx;
- the backend with gunicorn;
- HTTPS for the phone camera;
- daily backups;
- Telegram alerts;
- updates with a `git pull`.

You start from a Linux machine with Docker (Ubuntu, Debian…). In the examples, the server is **`192.168.1.50`** and its user is **`user`**. Replace them with yours.

### Step 1. Prepare the machine

```bash
# Docker, the compose plugin, git and make (Debian/Ubuntu)
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git make
sudo usermod -aG docker $USER     # to use docker without sudo (log out and back in)
```

> [!IMPORTANT]
> **Give the server a fixed IP**: reserve it in your router so it doesn't change. The HTTPS certificate, the links and the watchdog depend on it. Better if it's **wired**: some USB Wi-Fi adapters drop the network and leave the machine unreachable.

### Step 2. Get the code

```bash
mkdir -p ~/Development && cd ~/Development
git clone https://github.com/B0rjitaaa/DragonBall-EnhancedAPI.git
cd DragonBall-EnhancedAPI
```

The server always works on the **`main`** branch, the one you get by default.

### Step 3. Install in server mode

```bash
make install SERVER=192.168.1.50
```

It does the same as on your computer and, in addition:
- **Creates the production `.env`**, with `600` permissions:
  - random keys for Django, Postgres and the **administrator**. The admin password is shown at the end: keep it safe;
  - `COMPOSE_FILE` with `docker-compose.prod.yml`, for nginx and gunicorn;
  - `DJANGO_DEBUG=0`;
  - the IP in `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS`;
  - the backup folders (`BACKUP_DIR_HOST`, `BACKUP_STATUS_FILE`), and it creates `~/backups/dbs/request`.
- **Creates the HTTPS certificate** for the phone camera (`scripts/local-https.sh`) and enables port 443.
- **Enables automatic updates:** every `git pull` on `main` deploys by itself.

When it's done, open `http://192.168.1.50/` and log in at `http://192.168.1.50/admin/` with `admin` and the password it showed you.

### Step 4 (optional). Telegram alerts

1. Create a bot with **@BotFather** on Telegram and write down its token.
2. Send it a message and write down the chat id.
3. Add to `.env`:

   ```bash
   TELEGRAM_BOT_TOKEN=<bot token>
   TELEGRAM_CHAT_ID=<chat id>
   ```

4. Apply it with `docker compose up -d`.

Which alerts you get: [Scheduled tasks and alerts](tareas-programadas.md).

### Step 5. The certificate on each phone

For the phone to trust the certificate from step 3, **on each phone**:
1. Open `http://192.168.1.50/ca.crt` and download the profile.
2. **iPhone:**
   1. Settings → *Profile Downloaded* → Install.
   2. Settings → General → About → **Certificate Trust Settings** → turn it on.
3. **Android:** Settings → Security → Install certificate (CA).

Check that `https://192.168.1.50/scan` opens the camera. More in [Using the scanner](escaner.md).

### Step 6. Daily backups

Backups aren't made by Docker but by **systemd**, on the server itself. To install them:

```bash
make backups      # asks for the sudo password
```

It fills in the templates in `scripts/systemd/` with your user and the project folder, and enables:
- **the daily backup at 03:30.** If the machine was off at that time, it runs when it's turned on;
- the admin's **Back up now** button.

Try a backup by hand and see how it ends:

```bash
sudo systemctl start dbs-backup.service
journalctl -t dbs-backup -n 30
ls ~/backups/dbs/daily/
```

In the admin, **Backups** should say “✅ Last backup succeeded”. More in [Backups](copias-de-seguridad.md).

### Step 7. Final check

Go through the list in [What must be running](servicios.md):
- the 7 containers;
- the 2 systemd units;
- health at `ok`.

With this the server is complete. What follows is optional.

---

## Extras (optional)

None of this is needed to use the web app, but it covers two risks any home server has:
- **the server's disk breaks** and you're left without backups, because they were on the same disk;
- **the server goes down** and you don't find out, because it's the one sending the alerts.

For each risk there are two options: **another machine at home** if you have one (a Raspberry Pi, a NAS, another always-on computer) or an **external service** if you don't.

| Risk | With another machine at home | With an external service |
|---|---|---|
| Losing the backups | [rsync replica](#off-server-copy-on-another-machine-at-home) | [Cloud copy with rclone](#off-server-copy-in-the-cloud-rclone) or [on a VPS](#off-server-copy-on-a-vps) |
| Not finding out about an outage | [`watchdog.py` watchdog](#monitoring-with-another-machine-at-home) | [Heartbeat to Healthchecks.io](#monitoring-with-an-external-service-healthchecksio) |

Off-server copies are configured in the server's `~/.config/dbs-backup.env`, and you can use more than one at a time. In the admin, **Backups → “Off-server copy”** tells you whether the last one went well.

### Off-server copy: on another machine at home

The backups are replicated with **rsync** to another machine on the network (in the example, `192.168.1.60` with the user `user`). It uses an SSH key that **can only write backups** to one folder.

1. **On the server**, create the key:

   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/dbs_backup_ed25519 -N ""
   cat ~/.ssh/dbs_backup_ed25519.pub
   ```

2. **On the other machine**, authorize that key only to write to `~/backups-dbs`. Use `rrsync`, which comes with rsync (`sudo apt install rsync`):

   ```bash
   mkdir -p ~/backups-dbs
   # One line in ~/.ssh/authorized_keys:
   command="/usr/bin/rrsync -wo /home/user/backups-dbs",restrict ssh-ed25519 AAAA…(the public key)
   ```

3. **On the server**, add the destination to `~/.config/dbs-backup.env`. It ends in `:` because `rrsync` already fixes the folder:

   ```bash
   BACKUP_REMOTE=user@192.168.1.60:
   ```

4. Run a backup (`sudo systemctl start dbs-backup.service`). The admin should show “Off-server copy: ✅ copied”.

> [!WARNING]
> The destination folder is an **exact replica**: anything that isn't on the server is deleted from it. Don't keep other files there.

### Off-server copy: in the cloud (rclone)

**rclone** copies the backups to almost any cloud storage:
- **Backblaze B2**: 10 GB free, recommended;
- **Google Drive**, **Dropbox** or **OneDrive**;
- **Amazon S3** and compatible services (Cloudflare R2, Wasabi…).

With 7 daily and 4 weekly backups it uses a few hundred MB.

1. **Install rclone** on the server:

   ```bash
   sudo apt install -y rclone          # or the latest version: curl https://rclone.org/install.sh | sudo bash
   ```

2. **Create the “remote”** with the wizard. Example with Backblaze B2:
   1. On backblaze.com, create a private *bucket*, for example `mis-copias-dbs`, and an *Application Key* with access only to that bucket.
   2. On the server:

      ```bash
      rclone config
      # n (new) → name: b2 → type: b2 → account: the keyID → key: the applicationKey → the rest by default
      ```

   3. Check that it works: `rclone lsd b2:` should list the bucket.

   For **Google Drive** or **Dropbox** the wizard opens the browser to grant access. If the server has no screen, rclone explains how to authorize it from another computer (`rclone authorize`).

3. **(Recommended) Encrypt the backups** before uploading them. In `rclone config` create another remote of type **`crypt`** pointing to `b2:mis-copias-dbs/dbs`, with a password you **keep outside the server**: without it the backups can't be read.
4. **On the server**, add to `~/.config/dbs-backup.env`:

   ```bash
   BACKUP_RCLONE=b2:mis-copias-dbs/dbs        # or the encrypted remote, e.g. copias-cifradas:
   ```

5. Run a backup (`sudo systemctl start dbs-backup.service`) and check that it arrives: `rclone ls b2:mis-copias-dbs/dbs | head`. In the admin: “Off-server copy: ✅ copied”.

**To recover a backup** from the cloud, on any machine with rclone and the same remote:

```bash
rclone copy b2:mis-copias-dbs/dbs/daily/2026-10-29_0330 ./restaurar/
```

Then restore it as explained in [Backups](copias-de-seguridad.md#restoring).

### Off-server copy: on a VPS

If you have a **server on the Internet** with SSH (a VPS from Hetzner, OVH, DigitalOcean…), it works just like [with another machine at home](#off-server-copy-on-another-machine-at-home): the key restricted with `rrsync` on the VPS and, on the server:

```bash
BACKUP_REMOTE=user@mi-vps.example.com:
```

### Monitoring: with an external service (Healthchecks.io)

**Healthchecks.io** is free for up to 20 checks and alerts you via **Telegram**, email and other channels. You don't need to open ports or expose the server to the Internet.

It works like a “dead man's switch”: every 5 minutes the server sends it a **heartbeat**. It alerts you in two cases:
- **the heartbeat stops arriving**: server off, no Internet, or Celery or Redis down;
- **it arrives marked as a failure**: something critical on the server is down (database, workers…).

1. Create an account on **healthchecks.io** and click **Add Check**:
   - **Name:** DragonBall EnhancedAPI;
   - **Period:** 5 minutes;
   - **Grace time:** 10 minutes, so a restart doesn't trigger an alert.
2. In **Integrations**, add **Telegram**: the wizard gives you a bot to message. You can also use email.
3. Copy the check's **Ping URL** (something like `https://hc-ping.com/1234abcd-…`) and add it to the server's `.env`:

   ```bash
   HEALTHCHECKS_URL=https://hc-ping.com/1234abcd-…
   ```

4. Apply it with `docker compose up -d`. In a few minutes, the check on healthchecks.io turns **Up**.

To test it, stop the worker for a quarter of an hour (`docker compose stop celery_worker`): you'll get the alert. Then start it again with `docker compose start celery_worker`.

> [!TIP]
> Any service that supports “ping URLs” works the same way, for example **Better Stack (Heartbeats)** or **Cronitor**. The server sends a `POST` to the URL when everything is fine, and to `<URL>/fail` when something critical fails.

### Monitoring: with another machine at home

The **watchdog** (`scripts/watchdog.py`) runs on another machine on the network. Every 5 minutes it checks the server's health and alerts you on Telegram if it doesn't respond. It only needs Python, which already comes with Linux:

```bash
# On the other machine
mkdir -p ~/dbs-watchdog && cd ~/dbs-watchdog
curl -fsSLO https://raw.githubusercontent.com/B0rjitaaa/DragonBall-EnhancedAPI/main/scripts/watchdog.py
cat > watchdog.env <<'EOF'
HEALTH_URL=http://192.168.1.50/api/health/
TELEGRAM_BOT_TOKEN=<bot token>
TELEGRAM_CHAT_ID=<chat id>
EOF
chmod 600 watchdog.env
python3 watchdog.py watchdog.env --test     # you should get “👀 Watchdog active”
crontab -e
# */5 * * * * /usr/bin/python3 /home/user/dbs-watchdog/watchdog.py /home/user/dbs-watchdog/watchdog.env >> /home/user/dbs-watchdog/watchdog.log 2>&1
```

To update it, run the `curl` again. More in [Scheduled tasks and alerts](tareas-programadas.md#with-another-machine-at-home-the-watchdog).

### Scanner USB webcam

If the server has a webcam to scan without a phone, add to `.env`:

```bash
COMPOSE_PROFILES=camera
CAMERA_URL=http://camera:8080
CAMERA_DEVICE=/dev/video0
```

And apply it with `docker compose up -d`. The scanner will show **Scanner webcam**.

### What about running the whole server outside your home?

You can install everything on a **VPS** with the same steps in this guide, using its IP or domain in `make install SERVER=`. But today the web app **has no user accounts**: anyone who reaches it can see and change your collection. Until it has them, if you put it on the Internet protect it in front, for example with **Cloudflare Tunnel + Cloudflare Access** (sign-in with your email) or with a VPN like **Tailscale**.

---

## Updating an installation

| Where | How |
|---|---|
| On your computer | `git pull` and `docker compose up -d --build`. Migrations are applied automatically on startup. |
| On the server | `git pull` and nothing else: the deploy starts by itself. If not, `make deploy`. |

If you change the **`.env`** or the **volumes** in `docker-compose*.yml`, also run `docker compose up -d`.

## Uninstalling

```bash
docker compose down        # stops everything; the data stays in the volumes
docker compose down -v     # stops everything and DELETES the database, Redis and the files (irreversible!)
```

On a server, also:

```bash
sudo systemctl disable --now dbs-backup.timer dbs-backup-request.path
sudo rm /etc/systemd/system/dbs-backup*
```

## Installation problems

| Symptom | Likely cause | Solution |
|---|---|---|
| `port is already allocated` | Another program is using 5173, 8000, 5432 or 80 | Stop it, or change the port in `docker-compose.yml` or in `.env` (`HTTP_PORT`). |
| `env_file … required` or an error about `path` | Docker Compose too old | Update it to version 2.24 or later. |
| The backend restarts in a loop with “Postgres is not responding” | The database doesn't start | `docker compose logs db`. It's usually lack of disk space or a volume from another Postgres version. |
| The web app loads but without cards | The catalog wasn't imported | `docker compose logs backend \| grep -i import`. If `data/seed/` is missing, `git pull`; otherwise, `make sync` and wait. |
| I can't log in to the admin with admin / admin | There was already another administrator (previous installation), or it's a server | Use yours, or the password in `DJANGO_SUPERUSER_PASSWORD` in `.env`. To create another one: `make superuser`. |
| Bandai answers 403 or 429 in the logs | Too many requests | It pauses by itself and retries. If it keeps happening, raise `BANDAI_REQUEST_DELAY` in `.env`. |
| The scanner says “No matches: have the fingerprints been computed?” | The fingerprints are still being computed | Wait: they're computed by themselves after installing (`docker compose logs -f scanner_worker`). |
| The admin has no styles | The static files are missing | `docker compose restart backend` (it generates them on startup). |
| “CSRF … Origin checking failed” error when saving | You're using an address that isn't in `DJANGO_CSRF_TRUSTED_ORIGINS` | Add it to `.env` (comma-separated) and apply with `docker compose up -d`. |
| The phone camera won't open | Page without HTTPS or certificate not installed | Steps 3 and 5 (B). |
