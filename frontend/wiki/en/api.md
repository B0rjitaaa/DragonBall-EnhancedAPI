# REST API

Everything the web app does goes through a **JSON REST API**, and you can use it directly: for scripts, for other applications or to query data.

- **Interactive documentation (Swagger):** `/api/docs/`. For example, `http://localhost:8000/api/docs/` locally.
- **OpenAPI schema:** `/api/schema/`.

> [!WARNING]
> - **Open:** the API doesn't ask for a user, not even for writing (adding copies, logging matches…). Only launching a sync requires being an administrator. It's meant for the home network.
> - **Rate limit:** 1,000 requests per minute (`/api/errors/`, 30).
> - **CSRF:** if you're logged in to the admin, Django requires write requests to carry the `X-CSRFToken` header (the value of the `csrftoken` cookie) and the origin to be in `DJANGO_CSRF_TRUSTED_ORIGINS`. The web app does this by itself.

## Cards and catalog

| Method and path | What it does |
|---|---|
| `GET /api/cards/` | Listing with filters as parameters: `q`, `ordering`, `color=Red`, `energy_max=3`, `keyword=Barrier`… |
| `GET /api/cards/{id}/` | A card's details, with price, printings and price history. |
| `POST /api/cards/search/` | **Full search**, the same as in Search. See below. |
| `GET /api/cards/ref/{ref}/` | Turns a link (`BT20-149-2`) into the card's id. |
| `GET /api/cards/export/?updated_since=…` | Bandai's original records, in the same format as `cartas_dbs.json`. |
| `GET /api/fields/` | Fields that can be filtered and their operators. |
| `GET /api/facets/` · `POST /api/facets/` | Counts per value of each field: global or within a search. |
| `GET /api/banlist/` | The Banned/Limited list. |
| `GET /api/keyword-skills/` | Official keyword skills, their variants and the deck-building rules. |
| `GET /api/changes/?kind=&page=` | [News](novedades.md), 60 per page. |
| `GET /api/changes/count/?since=` | How many news items there are since a date. |
| `GET /api/sync/` · `POST /api/sync/ {"full": true}` | Sync history · launch one (administrators only). |
| `GET /api/health/` | [System status](tareas-programadas.md#health). 503 if something critical fails. |
| `GET /api/thumbs/{id}/{version}.webp` | A card's thumbnail. |
| `GET /api/prices/radar/?days=7\|30\|90&scope=collection\|all` | What's on the [Prices](pagina-precios.md) page: rising, falling, the most valuable and the value's evolution. |

### The search: `POST /api/cards/search/`

```json
{
  "q": "goku -\"super combo\"",
  "query": {
    "op": "or",
    "children": [
      {"op": "and", "children": [
        {"field": "type", "operator": "eq", "value": "LEADER"},
        {"field": "color", "operator": "has", "value": "Red"}
      ]},
      {"op": "and", "children": [
        {"field": "keyword_skill", "operator": "has", "value": "Counter : Play"},
        {"field": "energy", "operator": "lte", "value": 2}
      ]}
    ]
  },
  "ordering": "-power",
  "page": 1,
  "page_size": 48
}
```

**Parameters:**
- **`q`**: the free text, with the same syntax as in the web app.
- **`query`**: the [Advanced mode](modo-avanzado.md) tree:
  - **groups:** `{"op": "and"|"or", "not": false, "children": […]}`;
  - **conditions:** `{"field", "operator", "value", "not"}`.
- **`ordering`**: `number`, `name`, `energy`, `power`, `newest`; with `-` in front, reversed.
- **`page`** and **`page_size`**: page and size, up to 200.
- **`scope: "collection"`**: searches only in My collection. It adds each card's copies, the value to the response, and allows sorting by `quantity` or `position` (with `location`). It also accepts `include_fakes` and `fake`.

**Operators by field type:**
- **text:** `contains`, `eq`, `startswith`;
- **number:** `eq`, `ne`, `lt`, `lte`, `gt`, `gte`, `between`, `isnull`;
- **one of several:** `eq`, `in`;
- **list:** `has`, `has_any`, `has_all`, `is_empty`.

**Limits:** 6 levels, 60 conditions and 100 values per condition.

## My collection

| Method and path | What it does |
|---|---|
| `GET /api/my-collection/` | Collection summary. |
| `POST /api/my-collection/adjust/` | `{card_id, delta, location?, fake?}`: adds or removes copies (delta between −10 and 10). Answers **409** if the card is in several locations and you don't say which one. |
| `POST /api/my-collection/move/` | `{card_id, source, target, quantity, source_fake?, target_fake?, note_line?}`: moves copies. |
| `POST /api/my-collection/note/` | Changes the note of a card's copies in a location. |
| `POST /api/my-collection/reorder/` | A location's **My order** (from 1 to 500 ids). |
| `GET /api/my-collection/csv/` · `GET /api/my-collection/backup/` | Downloads in [CSV and JSON](importar-exportar.md). |
| `POST /api/my-collection/import/` | `{csv, apply}`: without `apply` it returns the preview; with `apply: true` it adds the copies. |
| `POST /api/my-collection/restore/` | `{backup, apply}`: restores the JSON backup **replacing** the collection. Without `apply`, the preview (before/after, changes per location and card, new or empty locations); with `apply: true`, it applies it all at once. |
| `GET` · `POST /api/my-collection/locations/` | Lists the locations (with Leader, warnings and value) or creates one. |
| `PATCH` · `DELETE /api/my-collection/locations/{id}/` | Edits or deletes a location. |

## Decks

They all hang from `/api/my-collection/`:

| Method and path | What it does |
|---|---|
| `GET decks/{id}/` | The box, the versions and the stats against each opponent Leader. |
| `POST decks/{id}/versions/` | Saves a new version of the list. |
| `POST decks/{id}/plan/` | Works out which copies would have to be moved to make a list the main one. |
| `POST decks/{id}/side/` | Changes the side deck copies. |
| `POST decks/{id}/matches/` | Logs a match. |
| `GET` · `POST decks/{id}/to-history/` | Preview · move the deck to the archive. |
| `POST decks/{id}/back-in-use/` | Puts an archived deck back in use. |
| `GET` · `PATCH` · `DELETE deck-versions/{id}/` | One version: view it, rename it or delete it. |
| `GET` · `POST deck-versions/{id}/restore/` | Plan · make a version the main one (moves copies). |
| `PATCH` · `DELETE matches/{id}/` | Edit or delete a match. |

## Scanner

They all hang from `/api/scanner/`:

| Method and path | What it does |
|---|---|
| `GET scans/` | Scans, 30 per page. Filters: `status`, `source`, `session`, `needs_review`, `added_to_collection`. |
| `POST scans/` | With `image` (multipart), recognizes that photo. Without it, captures from the server's webcam. Answers **202** and recognition continues in the background: poll `GET scans/{id}/` until it finishes. |
| `GET scans/{id}/` | The scan and its result. |
| `POST scans/{id}/confirm/` | `{card_id, copies?}`: confirms or corrects the card, and the scanner learns from the photo. |
| `POST scans/{id}/copies/` | Changes how many copies it adds (burst). |
| `POST scans/{id}/undo/` | Undoes an added scan. |
| `GET` · `POST sessions/` · `GET sessions/{id}/` | Burst or binder sessions. |
| `POST sessions/{id}/end/` | Ends a session. |
| `GET camera/preview/` | JPEG image from the server's webcam, or 503. |

## Others

| Method and path | What it does |
|---|---|
| `POST /api/errors/` | The web app reports its JavaScript errors (see [Error log](registro-de-errores.md)). |
| `/media/…` | Scan photos and own printing images. |

## Examples

```bash
# The 5 red cards with the most Power
curl -s -X POST http://192.168.1.50/api/cards/search/ \
  -H 'Content-Type: application/json' \
  -d '{"query":{"op":"and","children":[{"field":"color","operator":"has","value":"Red"}]},"ordering":"-power","page_size":5}'

# Which card is BT20-149-2?
curl -s http://192.168.1.50/api/cards/ref/BT20-149-2/

# System status
curl -s http://192.168.1.50/api/health/
```
