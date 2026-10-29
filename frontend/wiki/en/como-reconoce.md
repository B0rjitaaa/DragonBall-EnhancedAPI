# How cards are recognized

This article explains what the server does with each photo. You don't need it to use the scanner, but it helps you understand its percentages and why it sometimes hesitates.

## A photo's journey

```
Photo ─▶ crop and straighten ─▶ quick fingerprint (hash) ─┬─▶ clear? ─▶ result
                                                          └─▶ ORB (keypoints) ─▶ edition tie-break ─▶ result
```

### 1. Crop and straighten

The server looks for the **card's edges** in the photo, corrects the perspective and straightens it to 315 × 440 pixels. If it can't find the edges, it carries on with the whole photo and shows “card edges not detected” in the result.

### 2. Quick fingerprint (perceptual hash)

Every card in the catalogue has **fingerprints** computed from its official image (front and back), plus the photos you've confirmed. First the photo is compared with all those fingerprints, also rotated 180° in case the card is upside down.

If the best match is **very close** (distance ≤ 20) and the second one is clearly further away (a difference of 6 or more), that's it. The result shows the `hash` method, and it usually takes just a few milliseconds.

### 3. Keypoints (ORB)

If the quick fingerprint isn't enough, a more detailed comparison is made using **keypoints** (corners, strokes, text) of the best candidates:
- First the top 8 are checked.
- If none reaches 15 points in common, it widens to 48.
- The **confidence** (the percentage) comes from how many points match: 60 or more is 100%.

The result shows the `orb` method.

### 4. Tie-break between editions

The hard case is **printings of the same number** (regular, alt-art, SPR, tournament promos…), which sometimes differ only in the stamp or the foil. When the top two candidates share the same number:
- the photo is compared with all the printings of that number, **looking only at the areas where they differ**;
- if you have a **confirmed photo** of any of them, it's used instead of the official image (it looks more like what your camera sees);
- a 15% margin is needed to decide. If there isn't one, the scan goes to **Review**.

## The thresholds

| Threshold | Value | What it decides |
|---|---|---|
| Minimum confidence | **45%** | Below this, the scan is left as **To review**. |
| Add automatically (burst and binder) | **65%** | From here on, the card is added to the collection on its own. |
| Capture with no card | under 45% and no edges | In burst mode it's silently discarded. |

The thresholds can be tuned on the server with environment variables (see [Architecture](arquitectura.md#environment-variables)).

## The scanner learns with you

Every time you **confirm** or **fix** a card, its crop is saved as a new fingerprint of that card. Over time, the scanner gets better at recognizing your cards with your camera and your lighting, especially the alt-arts and promos that look alike.

## Speed

- **A worker of its own:** recognition runs in a dedicated process (`scanner_worker`) that handles photos one at a time. That way a busy scanner doesn't slow down the rest of the site.
- **Always warm:** it “warms up” every minute, so the first scan after a quiet spell doesn't take longer.
- **Timings:** the session panel shows how long each card took. If others were queued, it also shows the total time.

## Photos

Scan photos **aren't kept forever**:

- A task runs every hour (at minute 10) and **deletes photos older than 24 hours**.
- If they still take up more than **2 GB**, it deletes the oldest until they're down to **1.5 GB**.
- The scan record stays in the history, without the photo.
- **Learned fingerprints aren't lost**: they're in the database.
- Photos **aren't included in backups**.

## Catalogue fingerprints

When new cards enter the catalogue, their fingerprints are computed from the official images. Printings created by hand (promos that aren't on Bandai's site) also have a fingerprint, computed from the image they were given. See [Data and syncing](datos-y-sincronizacion.md#own-printings).
