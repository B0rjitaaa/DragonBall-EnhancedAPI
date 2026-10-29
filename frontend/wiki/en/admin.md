# The Django admin

The **admin** (`/admin/`) is Django's administration panel. None of this can be done from the regular web app: reviewing prices, looking at errors, launching backups or browsing the raw data.

![The admin home page with its sections](../img/admin.jpg)

## Logging in

- **On the server:** `http://192.168.1.50/admin/` (port 5173 also works) with the user `admin`.
- **Locally:** `http://localhost:8000/admin/` with **admin / admin**, which is created automatically on the first installation. To create another user, use `make superuser`.

The admin is in English and uses Madrid time.

> [!TIP]
> You can have the admin and the web app open at the same time in the same browser: the web app sends the security token (CSRF) that Django asks for when there's a logged-in session.

## Sections

| Section | What it contains | What you'll use it for |
|---|---|---|
| **Cards** | Cards, sync history (“sync runs”), **Banned/Limited list** and keyword skills | Looking at a card's raw data; checking whether the last sync went well. |
| **My collection** | Locations and collection entries (card + location + quantity + fake) | One-off lookups. For everyday use, use the web app. |
| **Decks: list versions and matches** | Each deck's versions with their matches | One-off lookups. |
| **Scanner** | Scans, sessions and card fingerprints | Reviewing a specific scan. |
| **Errors** | Failures in the web app, the server and the tasks | See [Error log](registro-de-errores.md). |
| **Backups** | Backup status, making one now and downloading them | See [Backups](copias-de-seguridad.md). |
| **Prices (Cardmarket)** | Expansions, products, links, prices, history, dollar/euro rate and **Review matches** | See [Reviewing prices in the admin](revisar-precios.md). |
| **Periodic tasks** | The scheduled tasks | Checking schedules. See the warning below. |
| **Authentication and Authorization** | Users and groups | Creating or changing admin users. |

## Sync history

![Sync history with Bandai](../img/admin-sync.jpg)

*Cards → Sync runs* lists every sync with Bandai:
- when it started and finished;
- whether it was **full**;
- how many cards it listed, created and updated;
- its status: **Running**, **Succeeded**, **With failures** (some cards couldn't be downloaded) or **Failed**.

If a sync fails, you also get a Telegram alert (see [Scheduled tasks and alerts](tareas-programadas.md)).

## Scheduled tasks (Periodic tasks)

*Periodic tasks* shows the automatic tasks and their schedule.

> [!IMPORTANT]
> Changes you make here **don't last**: when the task service restarts (which happens on every deploy), the schedules are loaded again from the code (`backend/config/settings.py`). To really change a schedule you have to change the code.

The complete list is in [Scheduled tasks and alerts](tareas-programadas.md).
