# Locations

A **location** is a place where you keep cards: a deck, a binder, a box… The **Locations** page (`/locations`) lists them all with their copies and value, and from it you create, edit and reorder them, and move decks to the archive.

![Locations: tabs by type, decks in use with their Leader's art, archive, binders and boxes](../img/ubicaciones.jpg)

## Location types

| Type | What for | On the page |
|---|---|---|
| **Deck** | A built deck. It has a Leader, versions, a side deck and matches: see [Decks](mazos.md). | **Decks** tab |
| **Binder** | Folders with 9-pocket sleeves. | **Binders** tab |
| **Storage** | Boxes of loose cards. | **Storage** tab |
| **Other** | Anything else. | **Other** tab, only if there are any |

There's also **Unsorted**: it always exists and **can't be deleted**. It's where these end up:
- scanned cards with no destination;
- cards added with **+** without choosing a location;
- the cards from a deck moved to the archive;
- the cards from a location that's deleted.

If Unsorted has copies, **“N unsorted copies · Sort them →”** appears at the top of the page and takes you to them so you can put them away.

> [!NOTE]
> This page doesn't move cards. To move them, use the [List view in My collection](mi-coleccion.md#list-view-moving-copies) (the link is in the header text).

## The tabs

At the top are **Decks**, **Binders**, **Storage** and **Other**, each with its count. As you scroll down the page, the active tab changes by itself to match the section you're looking at.

### Decks

**“In use N”:** one tile per deck with:
- its **Leader's art** (its Awaken side) and the colour dots;
- the deck's name and its Leader's name;
- **“N copies · M cards · €X”**: the value comes from Cardmarket and doesn't count fakes;
- **“N fakes”**, which takes you to the deck with fakes shown too;
- **⚠ N Banned · M Limited repeated**, if there are cards that can't be played. Hover to see the numbers.

**How the Leader is chosen:** it's the LEADER card in the box. If there are several, the genuine one you have the most copies of. If the box is empty, the Leader from its latest saved list is used.

**“Archive N”** (collapsible): decks you no longer play, “decks you no longer use; their latest list is saved”. Each one shows:
- how many copies are left in the box, or how many cards its latest list had;
- since when it has been archived, and “N times” if it has been archived more than once;
- the **Use again** button.

### Binders, Storage and Other

One row per location with:
- its name and notes;
- **“N copies · M cards · €X”** and “N fakes”;
- a bar comparing its size with the rest.

Tapping it opens that location in My collection.

## Creating a location

Each section has its own button: **+ New deck**, **+ New binder**, **+ New box** or **+ New location**. Type the name (unique, up to 80 characters) and press **Create**.

### Binder size

When you create a **binder**, you also choose its **Pockets per page**: **2×2** (4), **3×3** (9, the usual one and the default), **3×4** (12), **4×4** (16) or **Custom**, where you type rows × columns (up to 6 × 6). The size shows next to the binder's name in the list, for example **4×4**.

The scanner's [binder mode](escaner.md#binder-mode) uses it: the grid has that many slots and each copy's position note is counted with those columns. You can change it later in **Edit…**. Binders created before this option exist are 3×3.

## Reordering locations

With more than one location in a section, the **Reorder** button appears:
1. Drag each row by its **⠿** handle. On mobile, press and hold it for a moment before dragging.
2. Press **Done** to finish.

This order is the one used in every location selector on the site.

## The ⋯ menu on each location

### Edit…

The **Edit location** dialog lets you change:
- the **Name**;
- the **Type** (Deck, Binder, Storage, Other);
- for binders, the **Pockets per page**;
- the **Notes**, for example “blue box in the wardrobe”.

**Delete…** asks for confirmation: “Delete “Box 3”? Its N copies will move to “Unsorted”.” Scans that pointed to that location also move to Unsorted.

> [!WARNING]
> - A deck with **logged matches** can't be deleted. Delete its matches first or change its type.
> - The “in use / archived” status isn't changed by editing: it's changed with the options below.

### Move to archive (decks only)

When you take a deck apart:

1. **Move “Name” to the archive** opens, with the list of what's in the box, marking the Leader and the fakes.
2. Press **Move to archive**. Then:
   - if the box had cards, its list is saved as an automatic version **“When moved to archive”**;
   - all the copies, genuine and fake, move to **Unsorted**;
   - the side deck is emptied;
   - the deck moves to the archive and this is recorded in its log.
3. When it's done you can **Copy list**, which copies the text `2x BT1-001 Name`, so you know which cards to put away, or go to **View “Unsorted”**.

### Use again (archived decks only)

The deck goes back to **In use** and the site **brings a copy of its Leader** into the box, looking for it in this order:
1. Genuine copies first.
2. Unsorted first, then binders and boxes, and as a last resort other decks.

The notice tells you where it took it from; you get the rest of the cards back by restoring its latest version. If you don't have any copy of the Leader, the notice says so. **Open the deck** takes you straight there.

### Usage log…

Decks that have been archived at least once have a log with:
- how many times it has been archived and whether it's now in use or archived;
- each entry with date and time: **To the archive**, with how many copies left, or **Back in use**.
