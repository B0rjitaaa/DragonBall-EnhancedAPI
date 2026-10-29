# The Prices page

The **Prices** page (`/prices`) sums up the money side:
- how much your collection is worth and how it's changing;
- which cards are going up and down;
- which are the most valuable.

Below the title: “Cardmarket (Europe) checked against TCGplayer (US), every day. No fake copies or cards without sales.”

![The Prices page: the collection's value with its chart, and below it the cards going up, going down and the most valuable](../img/precios.jpg)

## The controls

- **My collection** / **Whole catalogue**: which cards are considered. By default, only yours (with at least one genuine copy).
- **7 days** / **30 days** / **90 days**: the period for rises and falls. By default, 30 days.

## Your collection's value

With **My collection** selected, the top shows:
- **“Your collection is worth €X”**;
- the change over the period (**▲ / ▼ N% in N days**);
- a **chart** of how it has evolved, with the start date, the minimum and the maximum.

So that the chart shows how **prices** change and not how many cards you've been adding, it's calculated with **the copies you have today** multiplied by each day's price. Only genuine copies count, and only prices that count in the value (with sales or set by hand).

With less than two days of history it says “The chart will appear once there are a few days of history.”

## Up, down and most valuable

Three blocks of up to 15 cards:

| Block | What it shows |
|---|---|
| **Up in N days** | The ones that rose the most, in percentage. |
| **Down in N days** | The ones that fell the most. |
| **Most valuable in your collection** (or **Most valuable**) | By current price. |

**Each tile shows:**
- the image;
- the change **▲ / ▼ N%**;
- the name, number and rarity;
- the current price and the previous one (**was €X**).

Tapping it opens its [details](ficha-de-carta.md).

**To appear in up or down**, a card must:
- have a price that counts in the value;
- be worth at least **€1**, before or now, so the list doesn't fill up with penny cards.

## While there isn't enough history

Our own history started on **28 October 2026**. Until it has as many days as the chosen period, rises and falls are calculated differently. A note at the top says so:

> Price history started on 28 October 2026. Until there are N days of our own history, rises and falls compare today's price with its **average sale price over the last 7 / 30 days on Cardmarket**.

In that mode:
- the 7-day period compares with the 7-day average, and the 30- and 90-day ones with the 30-day average;
- only cards with a Cardmarket price are included;
- jumps of more than 5 times are ignored, as they're usually a one-off sale rather than a real price change.

Once the history is long enough, the page will use its own without you having to do anything.
