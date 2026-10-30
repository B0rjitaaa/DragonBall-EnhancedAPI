# Using the scanner

The **Scanner** (`/scan`) recognizes cards with a camera and adds them to your collection. It works with:
- your **phone's camera**;
- the **USB webcam** connected to the server;
- a **photo** you upload.

It has three modes:
- **card by card**;
- **burst**, to keep swapping cards without touching the screen;
- **binder**, to scan a binder slot by slot.

![The scanner on a phone](../img/escaner.jpg)

## Before you start: the phone camera needs HTTPS

Browsers only allow the live camera on secure pages (**HTTPS**). At home the site runs over HTTP, so:

- **If you open it over HTTP**, the scanner says “The browser only allows the live camera over HTTPS.” and offers **Open the secure version**.
- **The secure version** uses a certificate of its own for the local network, which you have to **install once on each phone**:
  1. From the phone, open `http://192.168.1.50/ca.crt` and download it.
  2. **iPhone:** Settings → *Profile Downloaded* → Install. Then Settings → General → About → **Certificate Trust Settings** → turn it on.
  3. **Android:** Settings → Security → Install certificate (CA).
- **If you denied camera permission:** on iPhone, Settings → Chrome (or Safari) → Camera → Allow, then reload the page.

If none of this works, you can always use **Upload photo**.

> [!NOTE]
> The certificate is created with `scripts/local-https.sh <ip>` on the server. See [Development and deployment](despliegue.md).

## Choosing the camera

![The scanner on a computer](../img/escaner-escritorio.jpg)

- **This device's camera**: the phone's (the rear one) or the laptop's.
- **Scanner webcam**: a USB webcam connected to the server. The image arrives with about half a second of delay. If it's disconnected, it says “Scanner webcam unavailable (disconnected?). Retrying…”.

The site picks the device camera on phones and tablets and the server one everywhere else, but you can change it. Your choice is remembered.

**While scanning:**
- The screen **doesn't turn off**, even if you leave the phone still on a stand.
- A **frame** shaped like a card (63 × 88 mm) is always shown. Put the card inside it.
- In burst and binder mode, only what's inside the frame is sent.

## Card-by-card mode

1. Place the card inside the frame.
2. Press **Capture and identify** (or **Upload photo**).
3. While it works it shows “Identifying…”. When it's done, the **result** appears:
   - **“Identified · 92%”**: it recognized the card with that confidence;
   - **“Not sure · 38%”**: you need to review it (see [Reviewing uncertain scans](revisar-escaneos.md));
   - below, your cropped photo next to the details of the recognized card.
4. If it's right, press **Add to collection**: it adds 1 genuine copy to **Unsorted**. If it isn't, use **Not this card? Fix it**.

> [!NOTE]
> In card-by-card mode **nothing is added on its own**: you decide every time. To add in bulk, use burst mode.

## Burst mode

This is the mode for adding lots of cards in a row: **you put a card down, it recognizes it, adds it, and you put down the next one**, without touching the screen.

1. Choose **Save to**: the location the cards will go to, or **Unsorted**. It's remembered for next time.
2. Press **▶ Burst mode** with the frame area **empty**: for one second it learns what the background looks like.
3. Put cards down one at a time. At the top you can see what it's doing at each moment:
   - **“Waiting for a card…”**;
   - **“Movement: hold the card still”**;
   - **“Card still…”**;
   - **“Sending…”**.

   A new card is captured automatically once it has been still for 0.7 seconds and is different from the previous one.
4. Each capture appears in the **session panel**, with a sound:
   - **Added** (two rising tones): it recognized it with **65% or more** and added 1 copy to the chosen location.
   - **To review** (one low tone): it isn't sure. Press **Review** and pick the right card.
   - **Another copy?**: you put the same card down again without removing the previous one. It isn't added until you say so: choose how many with **− / +** and press **Add N copies**.
5. Press **■ End session** when you're done.

**The session panel:**
- At the top, the counters: **added**, **to review** and **undone**.
- Each row shows the thumbnail, the number and name, the confidence and how long it took.
- **Change how many copies:** use **− [n] +** on added cards. **PS** sets 4 at once (a playset).
- **Corrections:**
  - **Fix**: pick another card. It removes the wrongly added copy and adds the right one.
  - **Undo**: removes the copy that was added.
  - **Discard**: ignores a capture that's waiting for review.
- **Capture now** forces a capture without waiting for the detector.

> [!TIP]
> **To make burst mode run smoothly:**
> - Use a **plain, dark background**, with even light and no glare.
> - Take the card away and put the next one down in one clean movement. If the phone moves, the detector has to settle again.
> - If you start with a card already in place, that first one isn't captured automatically: use **Capture now**.

## Binder mode

To scan a binder **slot by slot**, with its page and position recorded:

1. Choose the destination in **Save to**, usually the binder itself. Next to it you'll see its page size, for example **▦ 3×3 · 9 pockets**: it's the one you chose for that binder in [Locations](ubicaciones.md#creating-a-location). If the destination isn't a binder (for example **Unsorted**), pick the size in **Binder pages**: 2×2, 3×3, 3×4 or 4×4. The site remembers your choice.
2. Press **▦ Binder mode**. A grid with one square per pocket appears (3 × 3 for the usual 9-pocket pages), along with **‹ Page N ›**.
3. The site tells you which slot is next: “Move the camera close to the card in **row 1, column 1** until it fills the frame”.
4. Press **Capture slot N**. If the sleeve is empty, press **Empty slot**.
5. When every pocket on the page is done, press **Next page →**.
6. Press **■ Finish** when you're done.

Each added copy stores its position in its **note**, for example “**P. 12 · row 2 · col 3**”, counted with the binder's own number of columns. That way you'll always know where each card is in the binder.

- **Redo a slot:** tap the slot in the grid. The new capture replaces the previous one.
- **What's added automatically:** the same as in burst mode (65% or more). The rest is left for review.

## The “History” tab

Next to **Scan** is **History**: every scan, 30 per page, with:
- **Date**;
- **Source**: “Camera” or “Uploaded photo”;
- **Result**;
- **Confidence**;
- **Time**.

Rows waiting for review are highlighted. Tapping a row opens its result.

> [!NOTE]
> **Photos are deleted** after 24 hours, or sooner if they take up more than 2 GB. The scan stays in the history, but without its photo it can no longer be confirmed or fixed. See [How cards are recognized](como-reconoce.md#photos).

## If a new version of the site comes out

During long sessions, if a new version is deployed, “A new version of the site is available.” appears at the top with a **Reload** button.
