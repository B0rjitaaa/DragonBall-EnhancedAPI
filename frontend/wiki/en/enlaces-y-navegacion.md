# Links, addresses and shortcuts

Almost everything you see on the site has **its own address**: a search, a card, a location or a deck. Copy the address from the browser and, when you open it somewhere else, you'll see the same thing. It's handy for bookmarking searches, sending a card to your phone or linking a deck.

## The pages

| Address | Page |
|---|---|
| `/` | [Search](buscar-cartas.md) |
| `/collection` | [My collection](mi-coleccion.md) |
| `/collection/location/<id>` | My collection inside a location (box, binder…) |
| `/collection/deck/<id>` | A [deck](mazos.md) |
| `/locations` | [Locations](ubicaciones.md) |
| `/prices` | [Prices](pagina-precios.md) |
| `/news` | [News](novedades.md) |
| `/scan` | [Scanner](escaner.md) |
| `/wiki` | This wiki |
| `/admin/` | [Django admin](admin.md) |

An address that doesn't exist shows the **“ERROR 404 · Page not found”** page, with buttons to go to Search or My collection.

A location's `<id>` is a fixed code: even if you rename the box or the deck, the link still works.

## Link to a card

![The “Copy link” button on the card page](../img/enlace-carta.jpg)

Any page that opens card pages accepts `?card=` with the **card number**:

- `?card=BT20-149` opens the **first** printing of BT20-149.
- `?card=BT20-149-2` opens the second, `-3` the third, and so on. They follow the order in which they were added. New printings always go at the end, so links you've already shared don't change.
- Old links with Bandai's internal number (`?card=54229`) still work.
- The number isn't case-sensitive: `?card=bt20-149` works too.

Examples:
- `http://192.168.1.50:5173/?card=BT20-149`: the card in Search.
- `http://192.168.1.50:5173/prices?card=P-428`: the card, opened on top of the Prices page.

To avoid typing it, use **🔗 Copy link** on the card page. When you open a card page the address changes to `?card=…` by itself, and when you close it, that part is removed again. If the number doesn't exist, it's dropped from the address without an error.

## The search in the address

Search and My collection write their state into the address, but only what isn't at its default value:

| Parameter | What it stores | Example |
|---|---|---|
| `q` | Search text | `?q=goku barrier` |
| `sort` | Order: `number`, `newest`, `-newest`, `name`, `energy`, `-energy`, `power`, `-power` (and in the collection `quantity`, `position`) | `?sort=-power` |
| `page` | Page, from 2 onwards | `?page=3` |
| `filters` | Sidebar filters, as JSON | `?filters={"color":{"values":["Red"],"match":"any"}}` |
| `advanced` | The [Advanced mode](modo-avanzado.md) tree, as JSON | |
| `advanced_on=0` | The tree is saved but the mode is OFF | |
| `view` | My collection: `grid`, `list` or `deck` | `?view=list` |
| `fakes=1` | My collection: show fakes too | |
| `card` | The open card | `?card=BT20-149` |

A complete example: red cards with Power 20000 or more, sorted from highest to lowest:

```
/?sort=-power&filters={"color":{"values":["Red"],"match":"any"},"power":{"values":[],"min":20000,"max":""}}
```

> [!TIP]
> Save the searches you repeat often (your Leaders, the Banned cards, the cards from a set) as **browser bookmarks**. It's the fastest way to get back to them.

### Old links

The site moved from Spanish addresses to English ones. Old links are converted automatically when you open them:
- `/coleccion` → `/collection`
- `/coleccion/mazo/…` → `/collection/deck/…`
- `/ubicaciones` → `/locations`
- `/escaner` → `/scan`
- `orden`, `pagina`, `vista`, `falsas`, `filtros`, `avanzado` → their English equivalents

## Keyboard shortcuts

| Key | Where | What it does |
|---|---|---|
| <kbd>Esc</kbd> | Card page | Closes it |
| <kbd>Esc</kbd> | Filters panel on mobile | Closes it |
| <kbd>Esc</kbd> | Enlarged image in the wiki | Closes it |
| <kbd>Enter</kbd> | Advanced mode values | Adds the typed value |
| <kbd>⌫</kbd> | Advanced mode values, with the box empty | Deletes the last value |

## The menu and the notices

- **The top menu** is the same on every page: Search, My collection, Locations, Prices, News, Wiki and Scanner.
- **Red notice under the menu:** something important is down. There are five cases:
  - the database isn't responding;
  - Redis isn't responding;
  - the scanner isn't available;
  - background tasks have stopped;
  - the server isn't responding.

  It's checked on load, every minute and when you come back to the tab. **×** (**Dismiss notice**) hides it in that tab, but it comes back if what's failing changes. See [Scheduled tasks and alerts](tareas-programadas.md#health).
