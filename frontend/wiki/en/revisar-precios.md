# Reviewing prices in the admin

Automatic matching with Cardmarket is almost always right, but there are cases it can't decide on its own: promos, cards Cardmarket names differently, several printings with the same name… Those cases go to a review page in the admin:

**`/admin/prices/pricereview/`** (in the admin: *Prices (Cardmarket) → Review matches*)

![Review matches: tabs at the top and, for each card, its Cardmarket candidates and the other options](../img/admin-precios.jpg)

> [!NOTE]
> The review **only includes cards you have genuine copies of**: those are the ones that affect your collection's value.

## The tabs

| Tab | What's in it |
|---|---|
| **Your unmatched cards** | Cards without a Cardmarket product: none was found, or there were several and it couldn't decide. |
| **Suspect prices** | Cards with a single listing that's out of proportion for their rarity (see [suspicious prices](precios.md#suspicious-prices)). They don't count towards the value until you review them. |
| **Expensive cards with no sales** | Cards of €10 or more that only have one listing, with no sales. Often the card is matched correctly and is simply rare; other times, your copy is a different edition. |
| **Matched by order** | Groups of printings with the same name in a set, matched in rarity order, where something doesn't add up (a high rarity comes out cheaper than a low one), and cards matched with “Automatic (cheapest of several)”. |

Each tab shows how many cards it has. Cards are shown 25 at a time, sorted by set and number.

## What you can choose for each card

In the first three tabs, each card shows its image, number, rarity and set, and these options:

| Option | What it does |
|---|---|
| **A candidate product** | The Cardmarket products that could be this card, with their price, their name, “its set” or the expansion, and ↗ to open it on Cardmarket. “· current price” marks the one it has now. |
| **Not on Cardmarket** | The card has no product. It's left without a Cardmarket price (if it has TCGplayer, that one is used). |
| **by hand [ ] €** | Set the price yourself, for example `3.50` (a decimal comma also works). When you type in the box, the option is selected by itself. |
| **My copies are fake** | Your copies become [fakes](mi-coleccion.md#fake-copies) and stop counting towards the value. |
| **I have another edition:** (in “Expensive cards with no sales”) | Shows the other printings with the same number and their price. When you pick one, **your copies move to that printing**, in the same location and with their notes and fake mark. It's for when the scanner or the import pointed to the wrong edition. |

> [!TIP]
> Before choosing, open the candidate with **↗**: on Cardmarket you'll see the photo and can check that it's your edition (tournament stamp, foil, language…).

## Saving

At the bottom there's a **fixed bar** with **Clear all** and **Save changes (N)**. You can mark many cards and save them all at once. If you try to leave with unsaved changes, the page warns you.

**When you save:**
- Your choices **stay fixed**: the daily update doesn't change them.
- They also apply to **identical reprints**: same number, rarity and set.
- The price of those cards is **recalculated right away**.
- A summary appears at the top: “Saved N cards (and their identical reprints): …”.

## The “Matched by order” tab

Here you don't go card by card, but **by groups**: the printings of the same name in a set (regular, alt-art, SPR…). For each printing there's a dropdown with the products of that name in the expansion.

- **They are fine as they are**: confirms the group as it is. It becomes “Chosen by hand” and doesn't show up again.
- **Save changes**: saves whatever you changed in the dropdowns.

## How each card was matched

In the admin, *Cardmarket links* shows each card's **method**:

| Method | Meaning |
|---|---|
| Automatic (only one) | There was only one product with that name in its set. |
| Automatic (by order) | Several printings with the same name: they were sorted by rarity and price. |
| Automatic (like its regular version) | Reprint: it copies the original printing's product. |
| Automatic (cheapest of several) | Several possible products: the cheapest one with sales was taken. |
| Chosen by hand | You chose it in the review. |
| Not on Cardmarket | You marked it. |
| Price set by hand | You set the price yourself. |

The last three are **manual** and the daily update always respects them.

## How often to review

You don't need to check it daily. Review the page:
- when a **new set** comes out and you've scanned it;
- when a price in your collection looks odd;
- every now and then, to see if there are new **suspect prices**.
