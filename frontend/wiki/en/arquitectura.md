# Architecture

How DragonBall EnhancedAPI is put together inside: what pieces it has, where each one runs and how they talk to each other.

## Overview

```
                         ┌───────────────────────────── server (192.168.1.50) ──────────────────────────────┐
  Browser / phone ─────▶ │ nginx (frontend)  ── /api, /admin ──▶  backend (Django + DRF, gunicorn)          │
   :80 · :443 · :5173    │   React SPA                                │                                     │
                         │                                            ├──▶ Postgres 16  (data)              │
                         │                                            ├──▶ Redis 7      (cache and queues)  │
                         │   celery_worker   ◀── queues ──  celery_beat (schedules)                         │
                         │   scanner_worker  (card recognition, «scanner» queue)                            │
                         │   camera (optional: USB webcam)                                                  │
                         │   systemd: daily backup 03:30 ──▶ (optional) another machine, cloud or VPS       │
                         └──────────────────────────────────────────────────────────────────────────────────┘
  Optional: heartbeat to Healthchecks.io, or watchdog on another machine at home ──▶ Telegram alerts
  External sources: Bandai TCG+ API · dbs-cardgame.com · Cardmarket · tcgcsv.com (TCGplayer) · ECB
```

## The pieces

| Service | Technology | What it does |
|---|---|---|
| **frontend** | React 19 + Vite + TypeScript. In production, built and served by **nginx 1.27** | The web app. nginx is also the front door: it passes `/api/`, `/admin/` and `/static/` to the backend and serves `/media/`. |
| **backend** | **Django 5.2** + Django REST Framework, with **gunicorn** in production | The REST API, the admin and all the logic. |
| **db** | **PostgreSQL 16** | All the data. |
| **redis** | **Redis 7** | Database 0: Celery queues. Database 1: cache (filters, keyword skills…). |
| **celery_worker** | Celery 5 | Background tasks: syncs, prices, alerts, imports. It recycles itself when it goes over about 250 MB of memory. |
| **scanner_worker** | Celery, `scanner` queue | The scanner's card recognition, one at a time. It keeps the fingerprints loaded in memory. |
| **celery_beat** | Celery beat + django-celery-beat | Launches the [scheduled tasks](tareas-programadas.md). |
| **camera** | Custom Python service (optional, `camera` profile) | Gives access to a USB webcam on the server (`/frame.jpg`, `/preview.jpg`, `/health`). |

## The Django apps

| App | Contents |
|---|---|
| `cards` | Catalog: cards, search and filters, sync with Bandai, ban list, errata, Q&A, keyword skills, news, thumbnails, health and alerts. |
| `collection` | Locations and copies (My collection). |
| `decks` | Deck versions, side deck and matches. |
| `scanner` + `vision` | Scans, sessions, fingerprints and image recognition (OpenCV). |
| `prices` | Cardmarket, TCGplayer, matches, each card's price, history and review. |
| `errorlog` | Error log and its alerts. |
| `backups` | The admin's backups page. |

## The servers

### server (production)

- **Address:** `192.168.1.50`, on the home network.
- **What runs:** all the services, with Docker Compose in production mode.
- **Project:** `/home/user/Development/DragonBall-EnhancedAPI`.
- **Backups:** in `/home/user/backups/dbs`.
- **How to reach the web app:**
  - `http://192.168.1.50/` (port 80);
  - `http://192.168.1.50:5173/` (kept for old links);
  - `https://192.168.1.50/` (443, for the phone camera).

### Outside the server (optional)

- **Backups:** a copy of the backups on another machine at home or on a VPS (rsync), or in the cloud (rclone).
- **Outage monitoring:** a heartbeat to Healthchecks.io, or the watchdog (`scripts/watchdog.py`) on another machine at home. See [Scheduled tasks and alerts](tareas-programadas.md#3-outage-monitoring-optional).

How to set it up: [Installation → Extras](instalacion.md#extras-optional).

## Production vs development

A single `docker-compose.yml` works for both. On the server, `docker-compose.prod.yml` is added on top, by setting `COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml` in its `.env`.

| | Development (your Mac) | Production (server) |
|---|---|---|
| **Backend** | `runserver` with auto-reload | `gunicorn` (1 worker, 4 threads) |
| **Frontend** | Vite with hot reload, on `:5173` | Built and served by nginx on `:80`, `:443` and `:5173` |
| **Code** | Mounted from your folder | Mounted from the server's clone |
| **Backups** | No | Mounts the backup folders for the admin page |

> [!WARNING]
> In `docker-compose.prod.yml`, each service's changes must go **after the whole `backend:` block**. On 26/10/2026 a misplaced block made `celery_worker` inherit gunicorn's command.

## nginx

In production, nginx (`frontend/nginx/`):
- serves the built web app; any unknown path returns `index.html` so React can resolve it;
- passes `/api/`, `/admin/` and `/static/` to Django. If the backend is down, `/api/` answers with a 503 JSON: “The server is not responding right now…”;
- serves `/media/` (scan photos, own images) and `/ca.crt` (the certificate for the phone camera);
- accepts uploads of up to 15 MB (scanner photos);
- has its own error pages (404 and 50x);
- enables **HTTPS** only if it finds `server.crt` and `server.key` in `./certs`. They're created by `scripts/local-https.sh` (see [Using the scanner](escaner.md#before-you-start-the-phone-camera-needs-https)).

## Environment variables

They're configured in the `.env` at the root (there's a `.env.example` template). **The real values and the secrets are only in each machine's `.env`.**

| Group | Variables |
|---|---|
| Django | `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS`, `LOG_LEVEL`, `API_ANON_RATE` |
| Postgres and Redis | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, `REDIS_URL` |
| Bandai and official websites | `BANDAI_API_URL`, `BANDAI_GAME_TITLE_ID`, `BANDAI_REQUEST_DELAY`, `BANDAI_WORKERS`, `BANLIST_URL`, `ERRATA_URL`, `CARD_FAQ_URL`, `KEYWORD_SKILLS_URL`, `IMPORT_ON_START` |
| Scanner | `MATCH_HASH_THRESHOLD`, `MATCH_ORB_CANDIDATES`, `MATCH_MIN_CONFIDENCE`, `AUTO_ADD_MIN_CONFIDENCE`, `SCAN_RETENTION_HOURS`, `SCAN_PHOTOS_MAX_MB`, `SCAN_PHOTOS_TARGET_MB`, `KEEP_WARM_SECONDS`, `CAMERA_URL`, `MEDIA_ROOT`, `CARD_IMAGES_DIR` |
| Webcam (camera service) | `CAMERA_DEVICE`, `CAMERA_WIDTH`, `CAMERA_HEIGHT`, `CAMERA_FPS`, `CAMERA_FOURCC`, `CAMERA_CONTROLS`… |
| Backups | `BACKUP_STATUS_FILE`, `BACKUP_DIR`, `BACKUP_REQUEST_DIR`, `BACKUP_DIR_HOST` |
| Prices | `CARDMARKET_GAME_ID` (13), `TCGPLAYER_CATEGORY_ID` (27) |
| Alerts | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `HEALTHCHECKS_URL` (outage monitoring from outside) |
| Compose and build | `COMPOSE_FILE`, `COMPOSE_PROFILES`, `HTTP_PORT`, `HTTPS_PORT`, `VITE_HTTPS_PORT`, `RUN_MIGRATIONS` |
| Deployment | `SKIP_PULL`, `FORCE`, `SKIP_DEPLOY_HOOK` |

## Security

- **Network:** the web app is meant for the **home network** and isn't exposed to the Internet.
- **API:** it's **open**, also for writing. Only launching a sync (`POST /api/sync/`) requires being an administrator.
- **Admin:** requires a username and password.
- **To do:** user accounts and hardening the server (published Postgres and backend ports, key-only SSH access). This has to be done before opening the web app outside your home.
