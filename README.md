# DragonBall-EnhancedAPI

Advanced card search for the **Dragon Ball Super Card Game** (BT1–BT31, promos, starter decks, expansions…)
with filters on every `card_config` attribute, on skills (`[Activate: Main]`, `[Limit 1]`,
`[Counter: Play]`…) and nested **AND / OR / NOT** searches.

> 📖 **Full documentation in the [wiki](frontend/wiki/README.md)** (also on the web, at `/wiki`): how to use each section, prices, scanner, admin, architecture, scheduled tasks, deployment and API.

| Service         | Technology                         | Port |
|-----------------|------------------------------------|------|
| `frontend`      | React 19 + Vite + TypeScript       | 5173 |
| `backend`       | Django 5.2 + Django REST Framework | 8000 |
| `celery_worker` | Celery (background tasks)          | —    |
| `celery_beat`   | Celery Beat (scheduled tasks)      | —    |
| `db`            | PostgreSQL 16                      | 5432 |
| `redis`         | Redis 7 (broker + cache)           | 6379 |

## Getting started

```bash
git clone https://github.com/B0rjitaaa/DragonBall-EnhancedAPI.git && cd DragonBall-EnhancedAPI
docker compose up -d              # or `make install`, which also waits and prints a summary
# On a home server (nginx, HTTPS, random keys, deploy on git pull): make install SERVER=<ip>
```

- Web: <http://localhost:5173>
- API: <http://localhost:8000/api/> · Swagger: <http://localhost:8000/api/docs/>
- Admin: <http://localhost:8000/admin/> (**admin / admin**, created automatically; on a server, a random password)

No `.env` is needed: `.env.defaults` has values for local use; a `.env` only changes what you want.

The repository ships the catalog and the prices (`data/seed/`): with an empty database they are imported
automatically at startup (if there is a more recent dump in `data/cartas_dbs.json` or `data/precios_dbs.json`, that
one is used), and the scanner fingerprints are computed by themselves in the background. `make seed` refreshes
`data/seed/` with the data from an installation. Step by step in the [wiki](frontend/wiki/README.md).

## Updating after a `git pull` (migrations included)

```bash
make deploy   # git pull + rebuild if dependencies changed + migrations + backend/Celery restart
```

To make it happen automatically on every `git pull` on `main` (recommended on the server),
enable the repository hook once:

```bash
make hooks    # = git config core.hooksPath .githooks
```

From then on, `git pull` runs `scripts/deploy.sh`: it rebuilds images only if
`requirements.txt`, `package.json` or the Dockerfiles change, applies migrations and restarts the backend and Celery.
To skip it once: `SKIP_DEPLOY_HOOK=1 git pull`.

## Production mode (server)

The server (`192.168.1.50`) uses production mode, which is lighter (saves ~250 MB). Add to `.env`:

```bash
COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml
```

- **Frontend:** a static build served by Nginx instead of the Vite server, on `:80`, `:443` (HTTPS, for the phone camera) and `:5173` (old links).
- **Backend:** gunicorn (1 process, 4 threads) instead of `runserver`. WhiteNoise serves the `/admin` static files.

`scripts/deploy.sh` detects it: in this mode, any change in `frontend/` rebuilds the static build.

In every environment, the Celery worker runs with concurrency 1 and `--max-memory-per-child`: after the daily sync, the process is recycled if it holds more than ~250 MB (it used to keep ~470 MB indefinitely).

## Bandai sync (Celery)

Scheduled in `config/settings.py → CELERY_BEAT_SCHEDULE` (Madrid time). It shows up in `/admin` → *Periodic tasks*,
but changes made there are lost when `celery_beat` restarts (every deploy): schedules are changed in `settings.py`.

| Task                         | When                      | What it does                                                    |
|------------------------------|---------------------------|-----------------------------------------------------------------|
| `check-health-alerts`        | Every 5 min               | Checks `/api/health/` and sends Telegram alerts                 |
| `scanner-keep-warm`          | Every 60 s                | Keeps the scanner recognition loaded                            |
| `scanner-cleanup-old-scans`  | Every hour (minute 10)    | Deletes scan photos older than 24 h (and above 2 GB)            |
| `sync-banlist-daily`         | Every day 03:30           | Official Banned/Limited list                                    |
| `sync-new-cards-daily`       | Every day 04:00           | Downloads only the new cards                                    |
| `sync-prices-daily`          | Every day 05:15           | Cardmarket, TCGplayer, dollar rate and the price of each card   |
| `purge-resolved-errors`      | Every day 05:30           | Deletes errors resolved more than 90 days ago                   |
| `sync-keyword-skills-weekly` | Mondays 03:45             | Official keyword skills and their texts                         |
| `sync-errata-weekly`         | Mondays 03:50             | Official errata                                                 |
| `sync-rulings-weekly`        | Mondays 03:55             | Official Card Q&A                                               |
| `sync-all-cards-weekly`      | Sundays 05:00             | Downloads every card again (errata, texts)                      |

Outside Celery: the daily backup (03:30, systemd on the server) and, if configured, outside downtime monitoring (Healthchecks.io or `scripts/watchdog.py` on another machine).
Details in the [wiki](frontend/wiki/README.md).

The client (`cards/bandai.py`) uses `curl_cffi` (Chrome fingerprint), rate-limits itself
(`BANDAI_REQUEST_DELAY`, `BANDAI_WORKERS`) and, if Bandai returns 403/429, pauses and retries.
It saves every 200 cards, so an interruption doesn't lose what was downloaded. History at `GET /api/sync/`.

## Banned and limited cards (Ban / Limit)

The official list (<https://www.dbs-cardgame.com/us-en/rule/banned-limited-cards.php>) is downloaded every day
at 03:30 (`sync-banlist-daily`) and sets `legality` = `banned` | `limited` | `legal` on every
printing of each `card_number`. The migration loads a copy bundled with the project
(`cards/data/banlist_snapshot.json`, updated on 19/06/2026) so it works from the very first start.

```bash
docker compose exec backend python manage.py sync_banlist             # force an update
docker compose exec backend python manage.py sync_banlist --snapshot  # go back to the local copy
```

`GET /api/banlist/` returns the list; in searches: `{"field": "legality", "operator": "in", "value": ["banned"]}`.

## Keyword skills (official names and texts)

Skills are classified as on <https://www.dbs-cardgame.com/us-en/rule/keyword-skills.php>:
**Activate Timing** (`timing`), **Keyword Skills** (`keyword_skill`) and **Keywords** (`keyword_rule`),
with the official name (`Over Realm X`, `Once per Turn`, `Counter : Play`…) and its text, which the web
shows on hover. The exact variant is still available in `keyword` (`Over Realm 3`).

- Only the card's **own** skills count (at the start of a line or chained). The ones
  mentioned inside a sentence ("it gains [Barrier]", "activates [Revive]") go to `keyword_mention`.
- What is not on the official website (e.g. `Z-Stack`, newer than its last update) shows up
  under Keyword Skills without a description.
- Updated every Monday at 03:45 (`sync-keyword-skills-weekly`); the migration loads a local copy.

```bash
docker compose exec backend python manage.py sync_keyword_skills             # force an update
docker compose exec backend python manage.py sync_keyword_skills --snapshot  # go back to the local copy
```

`GET /api/keyword-skills/` returns the skills with their text, their variants and the alias map.

## API

### Filterable fields — `GET /api/fields/`

| Type     | Fields                                                                                   | Operators                           |
|----------|------------------------------------------------------------------------------------------|-------------------------------------|
| text     | `name`, `text` (both sides), `card_number`                                                | `contains`, `eq`, `startswith`      |
| number   | `energy`, `power`, `back_power`, `combo_energy`, `combo_power`, `z_energy_cost`           | `eq`, `ne`, `lt`, `lte`, `gt`, `gte`, `between`, `isnull` |
| enum     | `type`, `rarity`, `series`, `set_code`, `card_set`, `legality`                            | `eq`, `in`                          |
| list     | `color`, `color_cost`, `character`, `special_trait`, `era`, `timing`, `keyword_skill`, `keyword_rule`, `keyword`, `keyword_mention`, `keyword_family`, `regulation` | `has`, `has_any`, `has_all`, `is_empty` |
| boolean  | `has_back`                                                                                | `eq`                                |

- `keyword`: exact normalized skill (`Activate: Main`, `Limit 1`, `Counter: Play`, `Once Per Turn`…).
  `[Activate : Main/Battle]` also counts as `Activate: Main` and `Activate: Battle`.
- `keyword_family`: groups variants (`Limit 1`/`Limit 2` → `Limit`, `Counter: Play`/`Counter: Attack` → `Counter`).
- `special_trait`, `character`, `era`, `color` are split on `/` (`Saiyan/Earthling` → `Saiyan` + `Earthling`).

### Nested search — `POST /api/cards/search/`

```json
{
  "q": "goku",
  "ordering": "-power",
  "page": 1,
  "query": {
    "op": "and",
    "children": [
      {"field": "type", "operator": "in", "value": ["BATTLE", "Z-BATTLE"]},
      {"field": "energy", "operator": "lte", "value": 3},
      {"op": "or", "children": [
        {"field": "keyword", "operator": "has", "value": "Counter: Play"},
        {"field": "keyword_family", "operator": "has_all", "value": ["Barrier", "Blocker"]}
      ]},
      {"field": "color", "operator": "has", "value": "Black", "not": true}
    ]
  }
}
```

Any node accepts `"not": true`. Limits: 6 levels and 60 conditions.
Ordering: `number` (natural: BT1, BT2… BT10), `name`, `energy`, `power`, `newest`; prefix `-` for descending.

### Quick filters via querystring — `GET /api/cards/`

`/api/cards/?color=Red&color=Blue&energy_max=3&keyword=Barrier&keyword=Blocker&keyword_match=all&q=vegeta`

Numbers: `field`, `field_min`, `field_max`. Lists: several values = OR (`field_match=all` for AND).
It also accepts `query=<JSON tree>`.

### Facets — `GET|POST /api/facets/`

Values and counts for each attribute (cached in Redis, invalidated after each import/sync).
`POST {q, query, only?}` returns the counts within a search.

## Useful commands

```bash
make import      # import data/cartas_dbs.json
make sync        # queue a sync (new cards only) · make sync-full for all of them
make test        # backend tests
make logs        # logs of every service
make reset       # deletes the database and Redis (careful!)
```

## Structure

```
backend/
  config/            settings, urls, celery
  cards/
    models.py        Card (normalized attributes + original JSON) and SyncRun
    parsing.py       card_config → fields; skill extraction and normalization
    query.py         AND/OR/NOT tree → Django Q (with validation)
    facets.py        counts per attribute (Postgres unnest) + Redis cache
    bandai.py        Bandai TCG+ client (rate limiting, retries, pause when blocked)
    tasks.py         sync_cards (Celery)
    importer.py      bulk upsert
frontend/src/
  App.tsx            state, search and shareable URL
  components/        FacetPanel, QueryBuilder, CardGrid, CardModal
  lib/               types, API client, query building
```

## To do / next steps

Pending work lives on the project's Trello board. The most important items:

- User accounts
- Server security: don't publish the Postgres and backend ports, key-only SSH
- Exposing the web outside home (Cloudflare Tunnel), after the above
