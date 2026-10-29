"""Novedades: detecta los cambios reales de cada sync comparando el antes y el después.

- Cartas (sync con Bandai): carta nueva, cambio de texto, imagen o atributos.
- Banlist: pasa a prohibida o limitada, o vuelve a ser legal.
- Erratas oficiales: errata nueva o modificada.
- Card Q&A: preguntas nuevas.

Si antes no había nada (primera importación o primera carga de una lista), no se registra:
serían miles de "novedades" que no lo son.
"""
from __future__ import annotations

from collections.abc import Iterable

from .models import Card, CardChange, Legality

Kind = CardChange.Kind

# Campo de la carta -> (tipo de cambio, nombre que se muestra)
CARD_FIELDS = {
    "name": (Kind.TEXT, "name"),
    "text": (Kind.TEXT, "text"),
    "back_name": (Kind.TEXT, "name (back side)"),
    "back_text": (Kind.TEXT, "text (back side)"),
    "image_url": (Kind.IMAGE, "image"),
    "energy": (Kind.STATS, "energy"),
    "color_cost": (Kind.STATS, "color cost"),
    "power": (Kind.STATS, "power"),
    "back_power": (Kind.STATS, "power (back side)"),
    "combo_energy": (Kind.STATS, "combo energy"),
    "combo_power": (Kind.STATS, "combo power"),
    "z_energy_cost": (Kind.STATS, "z-energy cost"),
}
LEGALITY_KIND = {Legality.BANNED: Kind.BANNED, Legality.LIMITED: Kind.LIMITED, Legality.LEGAL: Kind.LEGAL}
LEGALITY_LABEL = {Legality.BANNED: "Banned", Legality.LIMITED: "Limited", Legality.LEGAL: "Legal"}


def _text(value) -> str:
    return "" if value is None else str(value)


# --- Cartas -----------------------------------------------------------------------

def snapshot_cards(ids: Iterable[int]) -> dict[int, dict]:
    """Valores actuales de los campos vigilados de esas cartas (las que ya existen)."""
    return {row["id"]: row for row in Card.objects.filter(id__in=list(ids)).values("id", *CARD_FIELDS)}


def record_card_changes(before: dict[int, dict], ids: Iterable[int], run=None, catalog_was_empty: bool = False) -> int:
    """Compara con el estado tras el upsert y guarda los cambios. Devuelve cuántos."""
    fields = dict.fromkeys(["id", "card_number", "name", *CARD_FIELDS])
    after = Card.objects.filter(id__in=list(ids)).values(*fields)
    changes = []
    for card in after:
        old = before.get(card["id"])
        base = {"card_id": card["id"], "card_number": card["card_number"], "card_name": card["name"], "run": run}
        if old is None:
            if not catalog_was_empty:
                changes.append(CardChange(kind=Kind.NEW, **base))
            continue
        for field, (kind, label) in CARD_FIELDS.items():
            if _text(old[field]) != _text(card[field]):
                changes.append(CardChange(kind=kind, field=label, before=_text(old[field]),
                                          after=_text(card[field]), **base))
    CardChange.objects.bulk_create(changes)
    return len(changes)


# --- Listas oficiales (banlist, erratas, Q&A) ---------------------------------------

def _cards_by_number(numbers: Iterable[str]) -> dict[str, tuple[int, str]]:
    """La impresión de Bandai (id más bajo) de cada número, para enlazar el cambio."""
    out: dict[str, tuple[int, str]] = {}
    for card_id, number, name in Card.objects.filter(card_number__in=set(numbers)).order_by("id").values_list(
        "id", "card_number", "name"
    ):
        out.setdefault(number, (card_id, name))
    return out


def _change(kind, number: str, cards: dict, fallback_name: str = "", **fields) -> CardChange:
    card_id, name = cards.get(number, (None, fallback_name))
    return CardChange(kind=kind, card_id=card_id, card_number=number, card_name=name or fallback_name, **fields)


def record_banlist_changes(old: dict[str, str], new_entries: list[dict]) -> int:
    """old: {card_number: status} antes del sync."""
    if not old:
        return 0
    new = {e["card_number"]: e["status"] for e in new_entries}
    names = {e["card_number"]: e.get("card_name", "") for e in new_entries}
    cards = _cards_by_number(set(old) | set(new))
    changes = []
    for number in sorted(set(old) | set(new)):
        before, after = old.get(number, Legality.LEGAL), new.get(number, Legality.LEGAL)
        if before != after:
            changes.append(_change(LEGALITY_KIND[after], number, cards, names.get(number, ""), field="legality",
                                   before=LEGALITY_LABEL[before], after=LEGALITY_LABEL[after]))
    CardChange.objects.bulk_create(changes)
    return len(changes)


def record_errata_changes(old: dict[str, str], new_entries: list[dict]) -> int:
    """old: {card_number: texto corregido} antes del sync."""
    if not old:
        return 0
    cards = _cards_by_number(e["card_number"] for e in new_entries)
    changes = [
        _change(Kind.ERRATA, e["card_number"], cards, e.get("card_name", ""), field="errata",
                before=e.get("before", ""), after=e.get("after", ""))
        for e in new_entries
        if old.get(e["card_number"]) != e.get("after", "")
    ]
    CardChange.objects.bulk_create(changes)
    return len(changes)


def record_ruling_changes(old: set[tuple[str, str]], new_entries: list[dict]) -> int:
    """old: {(card_number, pregunta)} antes del sync. Se compara por el texto de la pregunta,
    no por su número, porque la web renumera al añadir preguntas."""
    if not old:
        return 0
    fresh = [e for e in new_entries if (e["card_number"], e["question"]) not in old]
    cards = _cards_by_number(e["card_number"] for e in fresh)
    changes = [
        _change(Kind.RULING, e["card_number"], cards, e.get("card_name", ""), field=f"Q{e['order']}",
                after=f"{e['question']}\n→ {e['answer']}")
        for e in fresh
    ]
    CardChange.objects.bulk_create(changes)
    return len(changes)
