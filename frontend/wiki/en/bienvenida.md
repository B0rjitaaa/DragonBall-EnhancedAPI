# Welcome to DragonBall EnhancedAPI

**DragonBall EnhancedAPI** is a website for **Dragon Ball Super Card Game** (Masters). It has four uses:
- **search** the whole card catalogue in much more detail than the official site;
- **manage your collection**: which cards you have, where they are and what they're worth;
- **build and track your decks**: list versions, matches and stats;
- **add cards with your phone's camera**.

It runs on your home network, on **the server**. Open it at `http://192.168.1.50/` from your computer or phone.

![Search, the main page](../img/buscador.jpg)

## The sections

The top menu is the same on every page:

| Section | What it's for | Start with |
|---|---|---|
| **Search** | The whole catalogue (over 9,000 printings), with text search, filters on any attribute and an advanced mode with AND / OR / NOT. | [Searching for cards](buscar-cartas.md) |
| **My collection** | The same as Search, but only with your cards: copies, locations, fakes and what it's all worth. | [My collection](mi-coleccion.md) |
| **Locations** | Your decks, binders and boxes, with their value, their Leader and their archive. | [Locations](ubicaciones.md) |
| **Prices** | What your collection is worth, how it changes over time and which cards are going up or down. | [The “Prices” page](pagina-precios.md) |
| **News** | New cards, text changes, ban list, errata and official questions. | [News](novedades.md) |
| **Wiki** | This guide. | — |
| **Scanner** | Recognises cards with the camera and adds them to your collection. | [Using the scanner](escaner.md) |

> [!TIP]
> **On your phone** the menu is a tab bar at the bottom, like an app: **Search**, **Collection**, **Locations**, **Scanner** and **More**, which opens **Prices**, **News** and **Wiki**. Card details open full screen, with the **✕** always at the top, and in My collection the backup and CSV buttons are folded under **Backup & CSV**.

And for admin tasks, the **Django admin** at `/admin/`: price review, errors and backups. See [The Django admin](admin.md).

## What it offers over the official site

- **Real search:**
  - by any word in the text, with exact phrases and exclusions;
  - by any attribute, combined however you like;
  - with counts on every filter.
- **Everything on one card page:** the card's information, its other printings, its price, its erratum, its Q&As and your copies.
- **Ban list always up to date**, applied to every printing and flagged in your decks.
- **Decks with a history:** list versions, side deck, matches against each Leader, deck-building rules checked, and an archive of decks you no longer play.
- **Prices** from Cardmarket cross-checked with TCGplayer, with daily history.
- **Scanner** with burst mode to add whole boxes.

## How it's built (in two lines)

- **Pieces:** a **Django** API with **PostgreSQL**, background tasks with **Celery** and **Redis**, and a **React** website, all in **Docker**.
- **Data:** comes from the **Bandai TCG+** API, the game's official site, **Cardmarket** and **TCGplayer**. It updates itself every day.

The details are in [Architecture](arquitectura.md).

## Where to go next

- **If you're going to install it:** [Step-by-step installation](instalacion.md).
- **If you're going to search for cards:** [Searching for cards](buscar-cartas.md) and [The card page](ficha-de-carta.md).
- **If you want to add your collection:** [Using the scanner](escaner.md) and then [My collection](mi-coleccion.md).
- **If you play:** [Decks](mazos.md).
- **If something isn't working:** [FAQ and troubleshooting](preguntas-frecuentes.md).
