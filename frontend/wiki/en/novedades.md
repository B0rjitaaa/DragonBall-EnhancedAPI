# News

The **News** page (`/news`) lists everything that has changed in the catalogue: new cards, text or image changes, the ban list, errata and new official questions. It's how you find out what Bandai has published without checking anything by hand.

![News grouped by day, with the filters by type at the top](../img/novedades.jpg)

## The menu badge

In the menu, next to **News**, an orange number shows the changes **since your last visit** to this page (up to “99+”). It disappears when you open the page.

> [!NOTE]
> “Your last visit” is stored **in this browser**. In another browser or on your phone the count is separate. If you've never opened News in a browser, everything counts there.

## What gets logged

| Type | When |
|---|---|
| **New card** | A card that wasn't there before appears on Bandai. |
| **Text change** | The name or text changes, on either side. |
| **New image** | Bandai changes the card's image. |
| **Attribute change** | Energy, Color Cost, Power, back-side Power, Combo Energy, Combo Power or Z-Energy Cost change. |
| **Banned** / **Limited** / **Legal again** | The official ban list changes. |
| **Official errata** | Bandai publishes an erratum. |
| **New question (Q&A)** | A new official question about the card appears. |

The first time something is imported (the whole catalogue, the ban list…) it is **not** logged as news; otherwise thousands of false changes would show up. Questions are compared by their text, because the official site often changes their numbering.

## What it looks like

- **Order:** changes are grouped **by day**, newest first, with **60 per page**.
- **Each change shows:**
  - the card's thumbnail (tap it to open its [card page](ficha-de-carta.md));
  - the type of change;
  - the **new** tag if it's later than your last visit;
  - the number and the name.
- **The detail depends on the type:**
  - **New card:** “New in the catalogue.”
  - **Text and errata:** two columns, **Before** and **After**.
  - **Question:** the question → the answer.
  - **Everything else:** “before → **after**”, for example “power: 10000 → **15000**”.

## Filtering

At the top there's a button for each type, with how many changes it has. You can tick several (they combine with OR). **show all** removes the filter.

> [!NOTE]
> - The numbers on the buttons are totals; they don't change when you filter.
> - The filter isn't stored in the address: when you reload the page it goes back to everything.

## When changes are checked

Changes arrive with the automatic syncs (Madrid time):

| What | When |
|---|---|
| New cards | Every day at 04:00 |
| Full catalogue check (text, image, attributes) | Sundays at 05:00 |
| Ban list | Every day at 03:30 |
| Keyword skills, errata and Q&A | Mondays at 03:45, 03:50 and 03:55 |

More detail in [Data and syncing](datos-y-sincronizacion.md).
