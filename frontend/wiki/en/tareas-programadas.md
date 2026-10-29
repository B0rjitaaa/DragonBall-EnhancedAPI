# Scheduled tasks and alerts

Almost all maintenance is automatic: syncs, prices, cleanup and backups. If something breaks, you get a **Telegram** message. Here's the complete list of what runs by itself and of when it alerts you.

## What runs by itself

All times are Madrid time.

| Time | Task | What it does |
|---|---|---|
| **Every 5 min** | Health alerts | Checks the system and alerts on Telegram if something fails (see below). |
| **Every minute** | Keep the scanner warm | Keeps recognition loaded in memory, so the first scan isn't slow. |
| **Every hour, at minute 10** | Clean up scan photos | Deletes those older than 24 h and, if they take up more than 2 GB, the oldest ones until it's down to 1.5 GB. |
| **03:30** | Ban list | Downloads the official Banned/Limited list. |
| **03:30** | Backup | Launched by systemd on the server, not Celery. See [Backups](copias-de-seguridad.md). |
| **04:00** | New cards | Quick sync with Bandai. |
| **05:15** | Prices | Cardmarket, TCGplayer, dollar rate and recalculation of prices and history. |
| **05:30** | Clean up errors | Deletes errors resolved more than 90 days ago. |
| **Monday 03:45 / 03:50 / 03:55** | Keyword skills / Errata / Q&A | Official lists from dbs-cardgame.com. |
| **Sunday 05:00** | Full sync | Downloads all the cards from Bandai again. |

Tasks that fail because of a temporary problem (the ban list, prices…) are **retried** automatically up to 3 times, waiting between attempts. No task can last more than 3 hours.

**Where the schedules live:**
- **Celery:** in `backend/config/settings.py` (`CELERY_BEAT_SCHEDULE`). You can see them, but not change them, in the admin, under *Periodic tasks*.
- **Backup:** in `scripts/systemd/dbs-backup.timer`.

> [!IMPORTANT]
> To change a schedule you have to edit `settings.py` and deploy. Whatever you change in the admin is lost when the services restart.

## Health

The **`/api/health/`** address returns the status of each piece of the system:

| Check | Type | Fails when… |
|---|---|---|
| Database | **Critical** | It doesn't respond. |
| Redis (cache and queues) | **Critical** | It can't write and read. |
| Celery worker | **Critical** | It doesn't answer within 1.5 s. |
| Scanner worker | **Critical** | It doesn't answer. |
| Bandai card sync | Warning | The last successful sync is more than 2 days old, or the last one failed. |
| Official banlist | Warning | It's more than 2 days old. |
| Official errata | Warning | It's more than 8 days old. |
| Official Card Q&A | Warning | It's more than 8 days old. |
| Cardmarket prices | Warning | They're more than 2 days old. |
| Backup | Warning | The last one failed, it's more than 30 h old, or the off-server copy failed (if configured). |
| Fixed station camera | Informational | It doesn't count towards the status. |

The overall status is:
- **`ok`**: all good;
- **`degraded`**: some warning is failing;
- **`down`**: something critical is failing. In that case the address answers with code 503.

**In the web app**, only **critical** failures are shown, as a red strip under the menu (see [Links, addresses and shortcuts](enlaces-y-navegacion.md#the-menu-and-the-notices)).

## Telegram alerts

All alerts go to the project's Telegram bot. There are three sources.

### 1. Health alerts (every 5 minutes)

- **🔴 Critical:** something critical has been down for **10 minutes**. It arrives **with sound**: “🔴 **Celery worker** for 12 min”.
- **🟡 Warning:** a warning (for example, the backup) alerts you the first time, **silently**.
- **✅ Working again:** when it's fixed: “It was failing for X”.

Each problem is reported **only once**, not every 5 minutes.

### 2. New errors

From the [Error log](registro-de-errores.md):
- **🐞 New error**;
- **🐞 A resolved error is back**.

They arrive silently and with the link to the admin.

### 3. Outage monitoring (optional)

Health alerts are sent by the server itself, so **if the server goes down, it can't alert you**. The same happens if Redis, the worker or `celery_beat` stop, since they're the ones that launch the alerts. To cover this there are two options, which can be used together.

#### With an external service: heartbeat to Healthchecks.io

If `HEALTHCHECKS_URL` is set in `.env`, every 5 minutes the server sends a **heartbeat** to Healthchecks.io (or another compatible service), and it's that service that alerts you:
- **if the heartbeat stops arriving**: server off, no Internet, or Redis, the worker or beat down;
- **if it arrives marked as a failure** (`/fail`): something critical is down, and the message says what.

You don't need to open ports: the server is the one making the call. How to sign up: [Installation → Monitoring with an external service](instalacion.md#monitoring-with-an-external-service-healthchecksio).

#### With another machine at home: the watchdog

The **watchdog** is a script (`scripts/watchdog.py`, using only Python's standard library). It runs on another machine on the network and every 5 minutes it queries `http://192.168.1.50/api/health/`. It alerts you about:
- **The server is not responding**;
- **The backend is not responding (the web loads, but without data)**;
- **Redis is down (scanner and tasks stopped)** or **Celery worker is down (sync and alerts stopped)**.

Like the rest, it alerts if it lasts 10 minutes, only once, and again when it's fixed. Its messages end with “(watchdog alert)”.

**Installing it on the other machine:**

```bash
mkdir -p ~/dbs-watchdog && cd ~/dbs-watchdog
curl -fsSLO https://raw.githubusercontent.com/B0rjitaaa/DragonBall-EnhancedAPI/main/scripts/watchdog.py
# watchdog.env (permissions 600): HEALTH_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
python3 watchdog.py watchdog.env --test   # “👀 Watchdog active”
crontab -e
# */5 * * * * /usr/bin/python3 /home/user/dbs-watchdog/watchdog.py /home/user/dbs-watchdog/watchdog.env >> /home/user/dbs-watchdog/watchdog.log 2>&1
```

Step by step in [Step-by-step installation](instalacion.md#monitoring-with-another-machine-at-home). The watchdog's log is in `~/dbs-watchdog/watchdog.log`.

> [!NOTE]
> The bot token and the chat are in the server's `.env` (and in `watchdog.env` if you use the watchdog). Without them, nothing is simply sent.
