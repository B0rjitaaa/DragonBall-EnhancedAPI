# Data

- **`seed/`** (in the repository): the catalog (`cartas_dbs.json.gz`) and the prices (`precios_dbs.json.gz`).
  With an empty database, the backend imports them by itself at startup, so a new installation has every
  card with its price from the very beginning. They are brought up to date with `make seed` (and a commit).
- **`cartas_dbs.json`** / **`precios_dbs.json`** (outside git): the most recent dumps; if they exist, they are
  used instead of the ones in `seed/`. The server rebuilds `precios_dbs.json` after each daily price download (05:15).
- `card_images/`, `scans/`: scanner caches (outside git).
