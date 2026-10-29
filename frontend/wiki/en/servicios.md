# What must be running

The complete list of everything that has to be running for the web app to work fully, where each thing runs and how to check it. Use it as a **checklist after installing** and as the **first stop when something fails**.

## Summary

```
Server
├── Docker Compose ── 7 containers always up (+ «camera» if there is a webcam)
│   ├── db · redis · backend · frontend
│   └── celery_worker · scanner_worker · celery_beat ── 11 scheduled tasks
├── systemd ── dbs-backup.timer (03:30) · dbs-backup-request.path («Back up now»)
└── git ── post-merge hook (deploys on every git pull)

Outside the server (optional; see «Extras» in Installation)
├── backups ── another machine at home (rsync) · the cloud (rclone) · a VPS
└── monitoring ── Healthchecks.io (heartbeat every 5 min) · watchdog.py on another machine at home
```

## 1. Docker containers

All seven, on the server and locally, must show as `running` in `docker compose ps`. If one goes down, it restarts by itself (`restart: unless-stopped`).

| Container | What it does | If it stops… | How to check it |
|---|---|---|---|
| **`db`** (PostgreSQL 16) | Stores all the data. | Nothing works. Red strip: “The database isn't responding: search and My collection don't work right now.” | `docker compose exec db pg_isready` |
| **`redis`** (Redis 7) | Cache and task queues. | The scanner and the tasks stop. Red strip. | `docker compose exec redis redis-cli ping` → `PONG` |
| **`backend`** (Django) | The API and the admin. In production, gunicorn with 1 process and 4 threads. | The web app loads, but empty: “The server isn't responding right now.” | `curl -s localhost:8000/api/fields/ \| head -c 80` |
| **`frontend`** | The web app. Locally, Vite on 5173. In production, nginx on 80, 443 and 5173, which also forwards `/api` and `/admin` to the backend. | The web app doesn't open. | Open the web app in the browser |
| **`celery_worker`** | Background tasks: syncs, prices, alerts, imports. It recycles itself when it goes over ~250 MB. | Nothing gets updated and no alerts arrive. Red strip: “Background tasks (Bandai sync, imports) are stopped.” | `docker compose exec celery_worker celery -A config inspect ping` |
| **`scanner_worker`** | Recognizes the scanner photos (`scanner` queue, one at a time). It loads the fingerprints into memory on startup. | The scanner doesn't identify anything. Red strip: “The scanner isn't available right now.” | `docker compose logs --tail 20 scanner_worker` |
| **`celery_beat`** | The clock: launches the scheduled tasks. | Nothing scheduled runs (sync, prices, alerts…), even though everything seems fine. | `docker compose logs --tail 20 celery_beat` |
| `camera` (optional) | The server's USB webcam. Only with `COMPOSE_PROFILES=camera`. | Only **Scanner webcam** fails; the phone keeps working. | `docker compose exec camera curl -s localhost:8080/health` |

> [!WARNING]
> If **`celery_beat`** stops, no health alert fires by itself: the alerts are launched precisely by beat. You'll notice because the data stops updating (News, prices) and, after 2 days, through the 🟡 “Bandai card sync” and “Cardmarket prices” warnings. If you set up **outage monitoring** (the heartbeat to Healthchecks.io or the watchdog on another machine), you'll find out right away: the heartbeat stops arriving as soon as beat stops.

### Starting, stopping and restarting

```bash
docker compose ps                         # status of all of them
docker compose up -d                      # starts whatever is missing (and applies .env or volume changes)
docker compose restart backend            # restarts one
docker compose restart backend celery_worker celery_beat scanner_worker   # what a deploy restarts
docker compose logs -f --tail 100 backend # live logs for one
docker compose down                       # stops everything (data is kept)
```

## 2. Scheduled tasks (inside `celery_beat`)

`celery_beat` launches them and the workers run them (the scanner ones, `scanner_worker`). **You don't have to start them by hand**: it's enough for the three Celery containers to be up. Madrid time.

| Task | When | What it does |
|---|---|---|
| `check-health-alerts` | Every 5 min | Checks health and alerts on Telegram |
| `scanner-keep-warm` | Every 60 s | Keeps recognition loaded |
| `scanner-cleanup-old-scans` | Every hour (min. 10) | Deletes scan photos older than 24 h, or if they go over 2 GB |
| `sync-banlist-daily` | 03:30 | Official ban list |
| `sync-new-cards-daily` | 04:00 | New cards from Bandai |
| `sync-prices-daily` | 05:15 | Cardmarket, TCGplayer, dollar and prices; then rebuilds `data/precios_dbs.json` |
| `purge-resolved-errors` | 05:30 | Cleans up errors resolved more than 90 days ago |
| `sync-keyword-skills-weekly` | Monday 03:45 | Official keyword skills |
| `sync-errata-weekly` | Monday 03:50 | Official errata |
| `sync-rulings-weekly` | Monday 03:55 | Official Card Q&A |
| `sync-all-cards-weekly` | Sundays 05:00 | Downloads the whole catalog again |

There are also tasks that launch by themselves when needed, with no schedule:
- **`identify_card`**, with each scanner photo;
- **`build_fingerprints`**, after a sync with new cards and when the `scanner_worker` starts if fingerprints are missing (new installation);
- **`notify_error`**, with each new error.

More in [Scheduled tasks and alerts](tareas-programadas.md).

## 3. System services on the server (systemd)

Outside Docker, on the server itself:

| Unit | What it does | How to check it |
|---|---|---|
| **`dbs-backup.timer`** | Launches the backup every day at 03:30 (or on boot, if the machine was off). | `systemctl list-timers dbs-backup.timer` → the next run should show |
| **`dbs-backup-request.path`** | Launches a backup when **Back up now** is clicked in the admin. | `systemctl status dbs-backup-request.path` → `active (waiting)` |
| `dbs-backup.service` | The backup itself (`scripts/backup.sh`). It isn't “running”: it runs and finishes. | `journalctl -t dbs-backup -n 30` |
| **`docker.service`** | Docker. It must start with the machine. | `systemctl is-enabled docker` → `enabled` |

## 4. Outside the server (optional)

Only if you've set up any of the [extras](instalacion.md#extras-optional):

| What | What it does | How to check it |
|---|---|---|
| **Off-server copy**: another machine, the cloud or a VPS | Keeps another copy of the backups, in case the server's disk breaks. | In the admin, **Backups** → “Off-server copy: ✅ copied” |
| **Healthchecks.io** | Alerts you if the server's heartbeat stops arriving. | The check is **Up** on healthchecks.io |
| **cron: `watchdog.py`** on another machine | Checks that the server responds and alerts on Telegram if it doesn't. | `crontab -l` · `tail ~/dbs-watchdog/watchdog.log` |

## 5. Once, when installing

They don't keep running, but without them something is missing:

| Run | What for | When to repeat it |
|---|---|---|
| `docker compose up -d` (or `make install`; on a server, `make install SERVER=<ip>`) | Services, catalog and prices from the repository and the admin user (admin / admin locally). On a server, also the `.env` with random keys, HTTPS and updating with `git pull` | Never: after that everything runs by itself |
| `make superuser` | Another admin user | If you want more than one |
| `scripts/local-https.sh <ip>` (done by `make install SERVER=`) | HTTPS certificate for the phone camera | If the IP changes, or after ~2 years (it expires after 825 days) |
| Install `ca.crt` on each phone | So the phone trusts the certificate | On each new phone |
| `make backups` | Daily and on-demand backups (systemd) | If the files in `scripts/systemd/` change |
| (Optional) `~/.config/dbs-backup.env` with `BACKUP_REMOTE` or `BACKUP_RCLONE` | Off-server copy | If the destination changes |
| (Optional) `HEALTHCHECKS_URL` in `.env`, or the watchdog's cron | Alerts when the server goes down | If `watchdog.py` changes (download it again with `curl`) |

## Quick check (all at once)

From the server:

```bash
cd ~/Development/DragonBall-EnhancedAPI
docker compose ps --format '{{.Service}}: {{.State}}'
curl -s localhost/api/health/ | python3 -m json.tool | grep -E '"(status|label|ok)"'
systemctl list-timers dbs-backup.timer --no-pager
systemctl is-active dbs-backup-request.path
```

What you should see:
- **the 7 containers** `running`;
- **health** with `"status": "ok"` and every check at `"ok": true`;
- **the timer** with its next run;
- **the request path** `active`.

If something doesn't add up, go to [FAQ and troubleshooting](preguntas-frecuentes.md#problems).
