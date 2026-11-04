# Tools

The **Tools** page (`/tools`) gathers the maintenance work, so it doesn't get in the way of the pages you use every day. It's in the top menu, next to **Wiki**; on a phone, inside **More**.

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
