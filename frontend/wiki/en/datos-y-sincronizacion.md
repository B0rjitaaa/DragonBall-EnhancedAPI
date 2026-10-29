# Data and syncing

The catalog isn't written by hand: it comes from **Bandai** and from the **official game website**, and it keeps itself up to date. This page explains where each piece of data comes from and how it's updated.

## The cards: Bandai TCG+

The complete catalog comes from the **Bandai TCG+ API** (the one behind the official app):
- `/card/list`: the list of ids, 500 at a time;
- `/card/{id}`: each card's details (texts, attributes, images, back side…).

So that Bandai doesn't cut off the requests:
- they're made looking like a browser;
- they go at a pace of one every 0.25 s, with 4 threads;
- if Bandai answers “too many requests” (403 or 429), everything pauses: one minute the first time, double each following time, up to 15 minutes;
- if it answers with a server error (5xx), it retries up to 8 times.

### The two kinds of sync

| Kind | When | What it does |
|---|---|---|
| **New cards only** | Every day at 04:00 | Downloads only the ids that aren't there yet. It's fast. |
| **Full** | Sundays at 05:00 | Downloads **all** the cards again, to detect text, image or attribute changes. |

Details:
- **Never two at once:** a lock in Redis prevents them from overlapping.
- **Saves in batches:** it saves every 200 cards, so an interruption doesn't lose what was already downloaded.
- **History:** each sync is recorded in the admin (*Sync runs*) with its result.
- **News:** the changes it detects go to [News](novedades.md).
- **When it finishes:** if there are new or changed cards, their fingerprints are computed for the scanner.

### Running it by hand

- **From the command line:**

  ```bash
  docker compose exec backend python manage.py sync_cards          # new ones only
  docker compose exec backend python manage.py sync_cards --full   # full
  ```

- **Through the API:** `POST /api/sync/ {"full": true}`, with an administrator session.

### From Bandai's JSON to the search fields

When each card is saved, its information is processed:
- **Attributes:** split into fields (Energy, Power, colors, Special Traits, Character, Era…).
- **Skills:** the ones in square brackets are extracted, distinguishing those the card **has** from those it only **mentions**.
- **Bandai's typos:** they're fixed (“Doube Strike” → “Double Strike”…) and quotes are unified.
- **Search text:** prepared so that brackets and capital letters don't matter.

## The official website: ban list, errata, Q&A and keyword skills

Four lists are downloaded from **dbs-cardgame.com**:

| List | When | What for |
|---|---|---|
| **Banned / Limited** | Every day at 03:30 | Marks which cards are banned or limited, and since when. It applies to **all printings** with the same number. |
| **Keyword skills** | Mondays at 03:45 | Official names and descriptions of the skills. It groups the variants (Over Realm 3, 4… → Over Realm X). |
| **Errata** | Mondays at 03:50 | The official errata: before and after text. |
| **Card Q&A** | Mondays at 03:55 | The official questions and answers per card. |

**If the official website fails or changes format, what was already there is kept.** For example, if the ban list comes back with fewer than 10 banned cards, it's considered broken and nothing is touched.

Each list has a **copy included in the code** (`backend/cards/data/*_snapshot.json`). That way a new installation has data from the start, and you can go back to it with `--snapshot`:

```bash
docker compose exec backend python manage.py sync_banlist --snapshot
```

## Images and thumbnails

- **Images:** the official ones are downloaded once to a local cache (`/data/card_images`). The scanner uses them to compute the fingerprints.
- **Thumbnails:** the grid uses **320 px WebP** thumbnails, generated the first time they're requested. Their address includes a hash of the original image, so if Bandai changes the image, the thumbnail regenerates by itself. The browser keeps them for a year.

## Own printings

Some printings are **not published** by Bandai in its API: Event Pack promos, tournament prizes, alternate foils… They can be added by hand from another printing of the same card:

```bash
docker compose exec backend python manage.py add_printing 5594 \
  --image https://…/imagen.png --set "Event Pack 09 (Alternate Foil)"
```

- **What it copies:** everything from the original card, with its own image and set. It doesn't copy the back side.
- **Its internal number:** from **900,000,000** upwards, so the Bandai sync never touches or deletes it.
- **Scanner:** its fingerprint is computed right away.
- **Backup:** its image goes to the `media` volume, which is backed up.
- **Price:** if it was created from a TCGplayer product, its price comes from that exact product.

## Prices

Cardmarket, TCGplayer and the dollar rate are downloaded every day at 05:15. See [Where each price comes from](precios.md).

## All the commands

They're run with `docker compose exec backend python manage.py <command>`:

| Command | What it does |
|---|---|
| `sync_cards [--full] [--async]` | Syncs with Bandai (by default, only the new ones). `--async` sends it to Celery. |
| `import_cards [path] [--if-empty]` | Imports cards from a JSON (`.json` or `.json.gz`). |
| `export_cards [path]` | Dumps the catalog (by default to `/data/seed/cartas_dbs.json.gz`). |
| `export_prices [path]` | Dumps the prices to `/data/precios_dbs.json` (done automatically every day; `.gz`, compressed). |
| `import_prices [path] [--if-empty]` | Loads the prices from a dump (replaces the existing ones). Without a path, the most recent one. |
| `sync_banlist [--snapshot]` | Updates the ban list. |
| `sync_errata [--snapshot]` | Updates the errata. |
| `sync_rulings [--snapshot]` | Updates the Q&A. |
| `sync_keyword_skills [--snapshot]` | Updates the keyword skills and reclassifies the cards. |
| `add_printing <base_id> --image URL --set "…"` | Adds an own printing. |
| `build_thumbs [--collection-only]` | Generates the missing thumbnails, your collection's first. |
| `build_fingerprints [--force] [--limit N]` | Computes the missing scanner fingerprints (it runs by itself when they're missing). |
| `download_card_images` | Downloads the missing official images. |
| `import_checker <dump>` | Imports the collection and decks from the old scanner (DragonBall-CameraCardChecker). |

`Makefile` shortcuts:
- `make install`, `make seed`, `make sync`, `make sync-full`, `make import`, `make export-prices`, `make import-prices`;
- `make shell`, `make psql`, `make migrate`, `make logs`, `make ps`, `make superuser`.

> [!CAUTION]
> `make reset` **deletes the database and Redis**.

## First installation

The first time it starts, the backend:
1. waits for Postgres;
2. applies the migrations, which load the included copies of the ban list, errata, Q&A and keyword skills;
3. if the database is empty, imports the catalog: `data/cartas_dbs.json` if it exists and, if not, the repository's (`data/seed/cartas_dbs.json.gz`);
4. if there are no prices, imports them the same way: `data/precios_dbs.json` or `data/seed/precios_dbs.json.gz`;
5. if there's no administrator, creates **admin / admin** (or the one in `DJANGO_SUPERUSER_*`).

After that, the `scanner_worker` computes any missing fingerprints by itself. It also works without dumps: `make sync` downloads the catalog from Bandai and prices are downloaded automatically as soon as there's a catalog. Step by step in [Step-by-step installation](instalacion.md).
