# Import, export and backup of the collection

In the [My collection](mi-coleccion.md) bar there are four buttons to get data out and bring it in:

| Button | What it does |
|---|---|
| **Download CSV** | Downloads your collection as a spreadsheet. |
| **Import CSV** | Adds the copies in a CSV to your collection. |
| **Download backup** | Downloads a full backup as JSON: locations, cards, copies, fakes and notes. |
| **Restore backup** | Returns your collection to the state in that backup (**replaces** it), with a preview and confirmation. |

![Download and import buttons in the My collection bar](../img/csv.jpg)

## Download CSV

Downloads `my-collection-YYYY-MM-DD.csv`, designed to open straight in **Excel with Spanish regional settings** (separator `;`, UTF-8 encoding with BOM). It has one row per card + location + genuine/fake:

| Column | Content |
|---|---|
| `id` | The card's internal Bandai number: identifies the exact printing. |
| `number` | BT20-149 |
| `name` | Card name |
| `set` | Set (expansion) |
| `location` | Location name |
| `quantity` | Copies |
| `fake` | `yes` / `no` |
| `notes` | That row's note |

## Import CSV

**Adds** the file's copies to your collection: it **doesn't delete or change anything** you already have.

1. Press **Import CSV** and then **Choose file…**.
2. The file is analysed and a preview appears: “**X** copies in **Y** rows (Z of them fake). N rows will be skipped.”, with the reason for each skipped row (“Row 12: Card not found…”).
3. If any location in the file doesn't exist, you're warned: those cards will go to **Unsorted**.
4. Press **Add X copies**. Everything is applied at once (all or nothing) and confirmed with “✔ Added **N** copies to your collection.”

### Accepted format

- **Separator:** `;`, `,` or tab. Detected automatically.
- **Headers:** case and accents don't matter, and Spanish names work too:

| Data | Valid headers | Required? |
|---|---|---|
| Card | `id` / `bandai_id`, **or** `number` / `card_number` / `número` | Yes, one of the two |
| Quantity | `quantity` / `qty` / `cantidad` / `copias` | Yes |
| Set | `set` / `card_set` / `edición` | If the number has several printings |
| Location | `location` / `ubicación` | No (empty → Unsorted) |
| Fake | `fake` / `falsa` (accepts `yes`, `y`, `sí`, `s`, `true`, `1`, `x`) | No |
| Notes | `notes` / `notas` | No |
| Name | `name` / `nombre` | No (informational only) |

- **How the card is found:** first by `id`. If there's no id, by number, and if that number has several printings, by set. If it's still ambiguous, that row is skipped with the warning “is ambiguous: add the id or set column”.
- **Locations:** matched by name, ignoring accents and case.
- **Notes:** added as a new line if that line wasn't there already.
- **Limits:** 2 MB and 20,000 rows.

> [!TIP]
> The CSV from **Download CSV** can be imported again as is. To move your collection to another installation: download it from one and import it into the other.

## Download backup (JSON)

Downloads `my-collection-YYYY-MM-DD.json` with:
- **all your locations**, including empty ones, with their type, copies, fakes and notes;
- **each card in each location**: id, number, name, quantity, fake and notes;
- the totals: cards, copies and fakes.

It's written with one line per location and one per card, so it's also easy to read in a text editor.

> [!TIP]
> Download a backup **before big changes**: reorganising locations, importing a large CSV or taking apart several decks. If something goes wrong, you restore it.

## Restore backup

**Restore backup** returns your collection **exactly** to the state in a JSON backup. Unlike **Import CSV**, which only adds, here **it's replaced**: anything not in the backup is removed.

![Restore backup preview: totals now and after, changes by location and the confirmation](../img/restaurar-copia.jpg)

1. Press **Restore backup** and choose the `.json` file you got with **Download backup** (**Choose backup (.json)…**).
2. **Preview.** Before anything changes, you see:
   - the backup's **date** (“Backup from …”);
   - **Now → After**: copies and cards, fakes included;
   - how many copies **are added** and how many **are removed**;
   - the **locations that will be created**, because they're in the backup but no longer exist;
   - the **locations that will be left empty**, which aren't deleted;
   - a table with each location that changes (**Now** and **After**);
   - **See the changes card by card**, with the +/− for each card in each location;
   - the backup's rows that **will be skipped**, for example cards that are no longer in the catalogue.

   If the backup is the same as your collection, it says so and there's nothing to apply.
3. To confirm, **type `replace`** in the red box. Until then the button is disabled.
4. Press **Replace my collection**. Two things happen:
   - **first a backup of your current collection is downloaded**, so you can undo it by restoring that backup the same way;
   - then everything is applied in one go: if anything failed, nothing changes.

**What's kept:**
- **Locations:** matched by name (ignoring accents and case) and none are deleted. Missing ones are created with their type and notes.
- **Decks:** they keep their **versions and matches**, which aren't in the backup. The side deck is adjusted so it doesn't have more copies than there are in the box.
- **My order:** cards that stay in the same location keep their place; new ones go at the end.
- **The notes** on each copy, as they come in the backup.

> [!NOTE]
> This backup only covers **your collection**. The backup of the whole database (prices, matches, scans…) is made automatically every night on the server: see [Backups](copias-de-seguridad.md).
