"""Mi colección en CSV: exportar para hojas de cálculo e importar sumando copias.

- Exportar: una fila por carta, ubicación y autenticidad, con `;` y BOM para que Excel
  en español lo abra en columnas.
- Importar: nunca borra nada, solo suma copias. Primero se devuelve una vista previa;
  al aplicar se vuelve a leer el CSV (no se confía en lo que mande el navegador) y
  solo entran las filas reconocidas. Las ubicaciones que no existen van a "Sin ubicar".
"""
from __future__ import annotations

import csv
import io
import unicodedata

from django.db import transaction

from collection.models import Location
from collection.services import add_copies

from .collection import fetch_export
from .models import Card

COLUMNS = ["id", "número", "nombre", "edición", "ubicación", "cantidad", "falsa", "notas"]
MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 20_000

# Cabeceras admitidas al importar (sin tildes y en minúsculas), también en inglés.
HEADER_ALIASES = {
    "id": "id", "bandai_id": "id",
    "numero": "number", "number": "number", "card_number": "number",
    "nombre": "name", "name": "name",
    "edicion": "set", "set": "set", "card_set": "set",
    "ubicacion": "location", "location": "location",
    "cantidad": "qty", "qty": "qty", "quantity": "qty", "copias": "qty",
    "falsa": "fake", "fake": "fake",
    "notas": "notes", "notes": "notes",
}
TRUE_VALUES = {"si", "s", "yes", "y", "true", "1", "x"}


class CsvImportError(ValueError):
    pass


def _plain(value: str) -> str:
    """'Ubicación ' -> 'ubicacion'."""
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    return value.strip().lower()


def export_csv() -> str:
    rows = fetch_export()
    sets = dict(Card.objects.filter(id__in={r["bandai_id"] for r in rows}).values_list("id", "card_set"))
    out = io.StringIO()
    out.write("﻿")  # BOM: Excel detecta UTF-8
    writer = csv.writer(out, delimiter=";", lineterminator="\r\n")
    writer.writerow(COLUMNS)
    for r in rows:
        writer.writerow([
            r["bandai_id"], r["card_number"], r["name"], sets.get(r["bandai_id"], ""),
            r["location"], r["quantity"], "sí" if r["fake"] else "no", r["notes"] or "",
        ])
    return out.getvalue()


def _reader(text: str) -> tuple[list[str | None], "csv._reader"]:
    text = text.lstrip("﻿")
    first_line = text.split("\n", 1)[0]
    delimiter = max((";", ",", "\t"), key=first_line.count)
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    try:
        header = next(reader)
    except StopIteration as exc:
        raise CsvImportError("El CSV está vacío") from exc
    keys = [HEADER_ALIASES.get(_plain(h)) for h in header]
    if "qty" not in keys or not ({"id", "number"} & set(keys)):
        raise CsvImportError("Faltan columnas: hace falta «cantidad» y «id» o «número»")
    return keys, reader


def parse_import(text: str) -> dict:
    """Vista previa: qué filas entran, cuáles no se reconocen y cuáles son ambiguas."""
    if len(text.encode("utf-8")) > MAX_BYTES:
        raise CsvImportError("El CSV pasa de 2 MB")
    keys, reader = _reader(text)

    raw_rows = []
    for line_no, values in enumerate(reader, start=2):
        if not any(v.strip() for v in values):
            continue
        if len(raw_rows) >= MAX_ROWS:
            raise CsvImportError(f"Más de {MAX_ROWS} filas")
        raw_rows.append((line_no, {k: (v or "").strip() for k, v in zip(keys, values) if k}))

    ids = {int(r["id"]) for _, r in raw_rows if r.get("id", "").isdigit()}
    numbers = {r["number"].upper() for _, r in raw_rows if r.get("number")}
    cards_by_id = Card.objects.in_bulk(ids)
    by_number: dict[str, list[Card]] = {}
    for card in Card.objects.filter(card_number__in=numbers).only("id", "card_number", "name", "card_set"):
        by_number.setdefault(card.card_number.upper(), []).append(card)
    locations = {_plain(loc.name): loc for loc in Location.objects.all()}
    default = Location.default()

    ok, errors, ambiguous = [], [], []
    for line_no, r in raw_rows:
        try:
            qty = int(r.get("qty") or "")
        except ValueError:
            errors.append({"line": line_no, "reason": f"Cantidad no válida: «{r.get('qty', '')}»"})
            continue
        if qty < 1:
            errors.append({"line": line_no, "reason": "La cantidad tiene que ser 1 o más"})
            continue

        card = cards_by_id.get(int(r["id"])) if r.get("id", "").isdigit() else None
        if card is None and r.get("number"):
            options = by_number.get(r["number"].upper(), [])
            if r.get("set"):
                same_set = [c for c in options if _plain(c.card_set) == _plain(r["set"])]
                options = same_set or options
            if len(options) == 1:
                card = options[0]
            elif len(options) > 1:
                ambiguous.append({"line": line_no, "number": r["number"], "qty": qty,
                                  "options": [{"id": c.id, "card_set": c.card_set} for c in options]})
                continue
        if card is None:
            label = r.get("id") or r.get("number") or "?"
            errors.append({"line": line_no, "reason": f"Carta no encontrada: «{label}»"})
            continue

        wanted = r.get("location", "")
        location = locations.get(_plain(wanted)) if wanted else default
        ok.append({
            "line": line_no, "card_id": card.id, "card_number": card.card_number, "name": card.name,
            "location_id": (location or default).id, "location": (location or default).name,
            "unknown_location": wanted if wanted and location is None else "",
            "qty": qty, "fake": _plain(r.get("fake", "")) in TRUE_VALUES, "notes": r.get("notes", ""),
        })

    return {
        "rows": ok,
        "errors": errors,
        "ambiguous": ambiguous,
        "totals": {
            "rows": len(ok),
            "copies": sum(r["qty"] for r in ok),
            "fakes": sum(r["qty"] for r in ok if r["fake"]),
            "unknown_locations": sorted({r["unknown_location"] for r in ok if r["unknown_location"]}),
            "skipped": len(errors) + len(ambiguous),
        },
    }


def apply_import(text: str) -> dict:
    """Vuelve a leer el CSV y suma las copias de las filas reconocidas (todo o nada)."""
    preview = parse_import(text)
    locations = Location.objects.in_bulk({r["location_id"] for r in preview["rows"]})
    cards = Card.objects.in_bulk({r["card_id"] for r in preview["rows"]})
    with transaction.atomic():
        for r in preview["rows"]:
            add_copies(cards[r["card_id"]], locations[r["location_id"]], r["qty"], r["notes"], r["fake"])
    return preview["totals"]
