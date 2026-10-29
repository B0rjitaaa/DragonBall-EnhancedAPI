# My collection

**My collection** (`/collection`) is Search, but only with the cards you own. It has the same search, the same filters, the same advanced mode and the same card page. On top of that, it has everything you need to manage your copies: how many you have, where they are, which ones are fake and what it's all worth.

![My collection: totals and value at the top, location and view controls, and the grid with − / + on each card](../img/coleccion.jpg)

## Copies, cards and locations

Three ideas to understand this part:

- **Card**: one specific printing (BT20-149 normal and BT20-149 alt-art are different cards).
- **Copy**: each physical copy you own of a card.
- **Location**: where each copy is. It can be a **deck**, a **binder**, a **storage** box or **another** place. There's always **Unsorted**, where things go that don't have a place yet (scans with no destination, cards that leave a deck…). More in [Locations](ubicaciones.md).

Each copy is also **genuine** or **fake** (see [Fake copies](#fake-copies)).

## The results bar

Above the cards:

- **“N cards · M copies”**: how many different cards and how many copies match the current search. By default only genuine copies count.
- **“value €X”**: what those genuine copies are worth, using each card's price.
  - **“(+ €Y in cards without sales)”**: the total of cards that only have one seller's listing. It's shown separately and isn't added to the total.
  - Hovering shows the breakdown, including copies with no price.

  How each price is calculated: [Where each price comes from](precios.md).
- **Location selector**: **All locations** or a specific one. Each shows its number of copies, fakes included.
- **Show fakes**: also counts and shows fake copies.
- **Locations…**: goes to the [Locations](ubicaciones.md) page.
- **View selector**:
  - **Grid**;
  - **List**;
  - **Deck**, only when the chosen location is a deck.
- **Download backup**, **Download CSV**, **Import CSV** and **Restore backup**: see [Import, export and backup](importar-exportar.md).
- **Scan cards**: opens the [Scanner](escaner.md).

> [!TIP]
> The value and the counters follow your filters. Filter by “Rarity: Secret Rare” and you'll see how many SCRs you have and what they're worth. Choose a location and you'll see what that box is worth.

## Sorting

You get the same options as in Search, plus two more:
- **Most copies**: cards you have the most copies of come first.
- **My order**: only with a location chosen. It's the order in which you've arranged the cards in that location (see [Reordering](#reordering-by-dragging)). When you choose a location, the order switches to **My order** automatically.

## “Grid” view

Each card shows the same as in Search, plus:
- **The location** (or “Box 1 ×2 · Binder ×1” if there are copies in several).
- **With Show fakes:** the “N fakes” badge.
- **Underneath:** the **− ×N +** buttons.

### Adding and removing with − / +

- **With a location chosen**, **+** and **−** add or remove in that location.
- **With All locations:**
  - **+** adds a genuine copy to **Unsorted**.
  - **−** removes from Unsorted first. If there are none there, it removes from the only other location the card is in.
  - If the card is in **several locations**, it doesn't guess which one to remove from: it opens the card page with the notice “This card is in several locations: remove the copy from the one you want.”
- **Without Show fakes**, **−** only removes genuine copies. With Show fakes, it removes genuine copies first and then fakes.

A card that reaches 0 copies disappears from the list straight away.

### Reordering by dragging

With a location chosen and the order set to **My order**, you can **drag the cards** to arrange them the way you actually have them (handy for a binder). The hint reminds you: “Drag the cards to reorder them (on mobile, press and hold a card). The order is saved.”

- **On a computer:** click and drag.
- **On mobile:** press and hold the card for a moment, then drag.
- **New cards** in a location go at the end.
- **Only the cards you're seeing are reordered.** Those on other pages or filtered out keep their place.

![My collection inside a location, sorted by hand](../img/coleccion-ubicacion.jpg)

## “List” view: moving copies

The list is mainly for **moving copies between locations**, one at a time or many at once.

![List view with selection checkboxes and the move control on each row](../img/coleccion-lista.jpg)

**Each row has:**
- the selection checkbox;
- the thumbnail (tap it to open the card page);
- the total **×N**;
- a tag per location with its quantity. Fakes carry “fake”, and the note shows on hover.
- the move control: **[n] from [source] to [destination…] → Move**.

The suggested source is the chosen location, or otherwise the one with the most copies. Fakes appear as “Box 1 (fakes)” and stay fake when moved.

**Moving many at once:**
1. Tick the cards, or use **Select all** for those on the page.
2. At the top, **“Move [all their copies | 1 copy] from [source] to [choose destination…] → Move N”** appears.
3. If any of the selected cards has no copies in the source, the button's tooltip says so.
4. **Clear selection** unticks everything.

> [!NOTE]
> **Notes when moving:**
> - If you move **all** the copies in a row, the note travels with them.
> - If you move only **some**, the note stays at the source.
> - From the card page you can choose **which line** of the note goes with the copy, for example its position in the binder.

## “Deck” view

When you choose a deck, the view switches to **Deck**: Leader, Main Deck, Z Deck and Side Deck, with their rules, stats, versions and matches. We explain it in [Decks](mazos.md).

## Fake copies

You can record any proxies or counterfeits you have as **fakes**, without mixing them with the genuine ones:

- **How they're marked:** by hand from the card page, with **Mark as fake** on the location's row. **It's genuine** does the opposite. Each click changes **one** copy.
- **How they're stored:** each card has, in each location, a row of genuine copies and another of fakes, each with its own note (e.g. “AliExpress, June”).
- **How new ones come in:** new copies (+, scanner, import without a `fake` column) always come in as genuine.
- **By default they don't count anywhere:** not in the counters, not in the filters, not in the value. To see them, tick **Show fakes**.
- **The collection value never includes them**, even when they're shown.

> [!IMPORTANT]
> A fake in a deck still counts in the **deck list**, because it's physically there. What it doesn't do is add to the value.

## Adding cards from Search

You don't need to go to My collection to add a card. On the page of any card in Search you have the panel with your copies, with **Add to My collection in [location] → Add**. See [The card page](ficha-de-carta.md#your-copies). In the Search grid, cards you own carry **×N**.

## Empty collection

If you don't have anything yet, the page says “Your collection is empty: scan cards with the scanner and they'll show up here.” There are three ways to fill it:
- the [Scanner](escaner.md);
- **Add** from a card's page;
- [importing a CSV](importar-exportar.md).
