# Tools

The **Tools** page (`/tools`) gathers the **change history** and the maintenance work, so it doesn't get in the way of the pages you use every day. It's in the top menu, next to **Wiki**; on a phone, inside **More**.

## History

Every change to your collection is recorded, one line per action, so you can see it and **undo it**:

- copies you add or remove by hand (**−** / **+**), move or mark as fake, and their notes;
- the scanner (each burst session is one line) and anything changed from the admin;
- locations created, changed or deleted, the order (**My order**) and the binder (moving a pocket, stacking copies, pages);
- decks: importing them, saving or deleting lists, making a version the main one, the side, **missing** cards, archiving them or bringing them back;
- importing a CSV and restoring a backup.

Wants and matches aren't included yet. The history starts counting from when it was installed: earlier changes aren't there.

**Tools** shows the latest changes; **Open the full history →** opens the full page (`/tools/history`), with search (a card by name or number), type of change, location or deck, source (web, scanner, admin) and dates. Each line says what happened, how many copies came in (**+**), went out (**−**) or moved (**⇄**) and when. Clicks in a row on the same card (say, five **+**) are merged into one line.

**Tap a line** to see the detail: card by card, how many copies were in each place before and after, and the binder position if it changed; plus everything else (deck created, new list, side…).

### Undo

**↶ Undo…** on a change puts everything back as it was: each copy goes back to its exact place, **binder position included**. Undoing a deck import, for example, returns the cards to the binders and boxes they came from, deletes the new deck, its list and its pick list, and removes the versions saved by the decks that gave cards.

You can undo **any change**, not just the last one, with a safeguard: if you touched those same cards afterwards, it won't undo blindly. It tells you which later changes modified them so you undo those first (newest first). An undo is also a line in the history (**UNDO**), and the undone change is marked **undone**.

### Redo

If you undid something by mistake, **↷ Redo…** applies it again exactly as it was. It shows on the undone change (marked **undone**) and on its **UNDO** line. Same safeguard: if you touched those cards afterwards, it warns you first. A redo is a **REDO** line, and it can be undone too.

### Export to CSV

**⇩ Export CSV** downloads the history, with whatever filters you have on, to open in Excel or Google Sheets. One row per card and place that changed: date, change, type, source, whether it's undone, card, location, copies before and after, difference and binder position. Changes that aren't copies (locations, lists, side…) get their own row, in the `other` column.

### Restore points

Right before **restoring a backup**, **importing a CSV** or **importing a deck**, a full copy of the collection is saved automatically (**⟲ point** on its line). At the bottom of the page, **Restore to this point…** shows how many cards would change and, once you confirm, puts everything back as it was at that moment, **including whatever you did afterwards**. It's for when something went very wrong; for normal use, **Undo** is enough. Going back to a point can be undone too. They're kept for **90 days** (the history, forever).

### In a card's details and in a deck

- Each card's details have **History of this card** (folded): the changes to its copies, of any printing.
- A deck's view has **History of this deck** at the end: what came in and out of its box, its lists and its side.

## Collection data

The four buttons to get data out of your collection and back in:

| Button | What it does |
|---|---|
| **Download backup** | Downloads a full JSON backup: locations, decks, wants and every copy. |
| **Restore backup** | Returns your collection to the state in that backup (**replaces** it), with a preview. |
| **Download CSV** | Downloads your collection as a spreadsheet. |
| **Import CSV** | Adds the copies in a CSV to your collection, with a preview. |

How each one works: [Import, export and backup](importar-exportar.md).

## System status

The same checks as `/api/health/`, each with a coloured dot:

- **green**: all good;
- **amber**: behind (e.g. prices or errata haven't been updated for days) or not set up on this machine;
- **red**: something critical is down (database, Redis, workers);
- **grey**: optional and not set up (the fixed camera).

It checks again by itself every minute, or with **↻ Check again**. When something critical goes down, the red strip at the top of the app links to this page. What each check looks at: [Scheduled tasks](tareas-programadas.md#health).

## Bandai sync

The last 10 catalog syncs: when they started, whether it was a full one (**Full**) or new cards only (**New cards**), the result, how long it took and how many cards were listed, new, updated and failed. If one failed, hover over it to see the error. **See what changed →** goes to [News](novedades.md).

Syncs run by themselves every day, and you can also start one now:

- **↻ Sync new cards**: only cards that aren't in the catalog yet, e.g. on the day a new set comes out. Takes a few seconds.
- **Full sync…**: downloads every card again and picks up text, image and errata changes. It takes an hour and a half, so it asks you to confirm (**Yes, full sync**).

While one is running the buttons are disabled and the table updates by itself. More in [Data and sync](datos-y-sincronizacion.md).

## Recent errors

The latest errors from the server, background tasks and the web app, **grouped** (the same failure shows once, with **×N** times). Tap one to see the request, where it happened and the full detail (traceback). Only open ones are shown by default; untick **Only open ones** to also see resolved ones.

You mark them as resolved in the admin: see [Error log](registro-de-errores.md).
