# FAQ and troubleshooting

## Usage

### How do I share a card with someone?

In its details, press **🔗 Copy link**. The link looks like `…/?card=BT20-149` and opens the card details directly. See [Links, addresses and shortcuts](enlaces-y-navegacion.md#link-to-a-card).

### Can I save a search?

Yes. The whole search (text, filters, sort, advanced mode) lives in the browser's address bar: bookmark it.

### Why doesn't my collection's value include all my cards?

The value only adds up:
- **genuine** copies: [fake](mi-coleccion.md#fake-copies) ones never count;
- cards with a **market price** (with sales) or a **price set by hand**.

Cards that only have a single seller's listing are shown **separately** (“+ €X in cards without sales”). Cards with a doubtful price don't count until they've been reviewed. Hovering over the value shows how many copies are left out and why. See [Where each price comes from](precios.md).

### A price looks wrong. How do I fix it?

1. In the card details, compare the sources (“Cardmarket €X · TCGplayer €Y”) and open **Offers in Europe ↗** to see the card on Cardmarket.
2. If it's matched with the wrong product, or you want to fix the price, go to the admin's [price review](revisar-precios.md). There you can choose the right product, set the price by hand, or move your copies to the right edition.

### I've made a mess of my collection. Can I go back?

Yes, if you have a **JSON backup** from before, the one from **Download backup**. Use **Restore backup** in **My collection**: you'll see what changes before applying it, and before replacing anything a backup of the current state is downloaded just in case. See [Restore backup](importar-exportar.md#restore-backup).

### I added a card to the wrong location

Open it in **My collection** and use **Move…** in its details, or the [List view](mi-coleccion.md#list-view-moving-copies), to move it.

### What happens to my cards if I delete a location?

They go to **Unsorted**: no copy is lost. A deck with logged matches can't be deleted; move it to the archive instead.

### How do I take a deck apart without losing its list?

In [Locations](ubicaciones.md), ⋯ menu → **Move to archive**. The list is saved as a version, the cards go back to **Unsorted** and the matches are kept. To build it again, **Use again**.

### The scanner added the wrong edition

- **During the session:** press **Fix** on that row.
- **Afterwards:** find it in **My collection** and remove the copy, or use the **“I have another edition”** option in the [price review](revisar-precios.md), which moves your copies to another printing.

Confirming the right one teaches the scanner for next time.

## Problems

### Saving something gives a “CSRF” error

The site always sends the security token, so this shouldn't happen. If it does:
- **“Origin checking failed”:** you're using an address that isn't in `DJANGO_CSRF_TRUSTED_ORIGINS` (for example, another IP or a `.local` name). Add it to the server's `.env` and apply it with `docker compose up -d`.
- **“CSRF token missing”:** the page is old. Reload it.

Any 403 is also recorded in the [error log](registro-de-errores.md).

### The phone camera won't open in the scanner

- **“The browser only allows the live camera over HTTPS”:** press **Open the secure version**. The first time you'll need to install the certificate on the phone (see [Using the scanner](escaner.md#before-you-start-the-phone-camera-needs-https)).
- **“Camera permission denied”:** on iPhone, Settings → Chrome (or Safari) → Camera → Allow, then reload.
- **As an alternative**, use **Upload photo**.

### Burst mode doesn't capture the cards

- Start with the frame area **empty**: it learns the background for one second.
- Keep each card **still** for a moment.
- Use a **plain background**, with even light and no glare.
- If you need to, **Capture now** forces the capture.

### A red strip appears under the menu

Something important on the server is down: the database, Redis, the scanner or the background tasks. If it lasts more than 10 minutes you'll also get a Telegram message. Check the server (see below).

### The site doesn't load at all

1. **Check that the server is on and connected to the network.** If you set up downtime monitoring (Healthchecks.io or the watchdog), you'll have received an alert.
2. **Log in over SSH and check the containers:**

   ```bash
   cd ~/Development/DragonBall-EnhancedAPI
   docker compose ps
   docker compose logs --tail 100 backend
   ```

3. **If any of them is stopped:** `docker compose up -d`.

### New cards that Bandai has already published are missing

New cards are checked for every day at 04:00. To avoid waiting:

```bash
docker compose exec backend python manage.py sync_cards
```

If the sync fails, look at *sync runs* in the admin and at the [errors](registro-de-errores.md).

### I got an alert that the backup failed

Open **Backups** in the admin: you'll see which step failed and the error message. Start another one with **Back up now**. If the only thing failing is the **off-server copy** (“Off-server copy: ❌ failed”), check the destination: the other machine switched on, or the cloud with `rclone lsd <remote>:`. See [Backups](copias-de-seguridad.md).

### I deployed and the changes don't show up

- **Browser:** reload without cache. The scanner shows the notice “A new version of the site is available”.
- **Volumes or `.env`:** if you changed them, run `docker compose up -d` on the server. Deploying only restarts containers.
- **Check** that `main` has your commits and that CI passed. See [Development and deployment](despliegue.md).
