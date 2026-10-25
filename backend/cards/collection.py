"""Mi colección vista desde el catálogo: copias por carta y su reparto por ubicación.

Las copias viven en la app `collection` (ubicaciones y filas de copias); aquí se
agregan por carta para el buscador, las facetas y las acciones de Mi colección.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field

from django.db import transaction

from collection import services
from collection.models import CollectionEntry, Location

from .models import Card

# Ya no hay caché (la colección está en esta misma base de datos): se mantiene el
# nombre para quien la invalidaba.
CACHE_KEY = "my-collection:owned"


class CollectionUnavailable(Exception):
    """Error de una acción de Mi colección, con el estado HTTP a devolver (y datos extra)."""

    def __init__(self, message: str, status: int, data: dict | None = None):
        super().__init__(message)
        self.status = status
        self.data = data or {}


@dataclass
class Owned:
    # id -> {quantity, fakes, locations: [{id, name, kind, quantity, fake, position, notes}]}
    cards: dict[int, dict] = field(default_factory=dict)
    numbers: dict[int, str] = field(default_factory=dict)  # id -> número de carta

    @property
    def ids(self) -> list[int]:
        return list(self.cards)

    @property
    def fingerprint(self) -> str:
        """Cambia en cuanto cambia la colección: sirve de clave de caché (facetas)."""
        raw = json.dumps(sorted((i, c["quantity"]) for i, c in self.cards.items()))
        return hashlib.sha1(raw.encode()).hexdigest()[:16]

    def quantity(self, card_id: int) -> int:
        return self.cards.get(card_id, {}).get("quantity", 0)

    def filtered(self, keep) -> "Owned":
        """Solo las cartas con alguna fila de copias que cumpla `keep`; `quantity` pasa a ser las de esas filas."""
        cards = {}
        for card_id, item in self.cards.items():
            here = sum(loc["quantity"] for loc in item["locations"] if keep(loc))
            if here:
                cards[card_id] = {**item, "quantity": here, "total_quantity": item.get("total_quantity", item["quantity"])}
        return Owned(cards, {i: n for i, n in self.numbers.items() if i in cards})


def fetch_export() -> list[dict]:
    """Una fila por carta, ubicación y autenticidad (también la usa la copia de seguridad)."""
    rows = CollectionEntry.objects.select_related("card", "location").order_by(
        "card__card_number", "card_id", "-location__is_default", "location__position", "location__name", "fake"
    )
    return [
        {
            "bandai_id": e.card_id,
            "card_number": e.card.card_number,
            "name": e.card.name,
            "quantity": e.quantity,
            "location_id": e.location_id,
            "location": e.location.name,
            "location_kind": e.location.kind,
            "fake": e.fake,
            "position": e.position,
            "notes": e.notes,
        }
        for e in rows
    ]


def fetch_owned() -> Owned:
    cards: dict[int, dict] = defaultdict(lambda: {"quantity": 0, "fakes": 0, "locations": []})
    numbers: dict[int, str] = {}
    for entry in fetch_export():
        item = cards[entry["bandai_id"]]
        item["quantity"] += entry["quantity"]
        item["fakes"] += entry["quantity"] if entry["fake"] else 0
        item["locations"].append({
            "id": entry["location_id"],
            "name": entry["location"],
            "kind": entry["location_kind"],
            "quantity": entry["quantity"],
            "fake": entry["fake"],
            "position": entry["position"],
            "notes": entry["notes"],
        })
        numbers[entry["bandai_id"]] = entry["card_number"]
    return Owned(dict(cards), numbers)


def _summary(card: Card) -> dict:
    result = services.card_summary(card)
    return {"quantity": result["quantity"], "fakes": result["fakes"], "locations": result["locations"]}


def _card(card_id: int) -> Card:
    card = Card.objects.filter(id=card_id).first()
    if card is None:
        raise CollectionUnavailable("Carta desconocida", 404)
    return card


def _location(location_id: int | None) -> Location | None:
    if location_id is None:
        return None
    location = Location.objects.filter(id=location_id).first()
    if location is None:
        raise CollectionUnavailable("Ubicación desconocida", 400, {"location": "Ubicación desconocida"})
    return location


def adjust_owned(card_id: int, delta: int, location: int | None = None, fake: bool | None = None) -> dict:
    """Suma o resta copias de una carta. Devuelve {quantity, fakes, locations} tras el cambio.

    Al sumar, las copias entran en `location` ("Sin ubicar" por defecto). Al restar sin
    `location`, se quitan de "Sin ubicar" y, si no llega, de la única otra ubicación con
    copias; si hay varias, 409 con el reparto (CollectionUnavailable.data) para elegir.
    """
    card, where = _card(card_id), _location(location)
    if delta > 0:
        services.add_copies(card, where or Location.default(), delta)
    else:
        try:
            services.remove_copies(card, -delta, where, fake)
        except services.AmbiguousLocation as exc:
            raise CollectionUnavailable(str(exc), 409, _summary(card)) from exc
    return _summary(card)


def move_owned(card_id: int, source: int, target: int, quantity: int,
               source_fake: bool = False, target_fake: bool | None = None, note_line: str | None = None) -> dict:
    """Mueve copias; con source == target y target_fake distinto, las marca como falsas o auténticas."""
    card = _card(card_id)
    try:
        services.move_copies(card, _location(source), _location(target), quantity, source_fake, target_fake, note_line)
    except ValueError as exc:
        raise CollectionUnavailable(str(exc), 400) from exc
    return _summary(card)


def note_owned(card_id: int, location: int, notes: str, fake: bool = False) -> dict:
    card = _card(card_id)
    updated = CollectionEntry.objects.filter(card=card, location=_location(location), fake=fake).update(notes=notes)
    if not updated:
        raise CollectionUnavailable("No hay copias de esa carta en esa ubicación", 404)
    return _summary(card)


KIND_NAMES = {"deck": "mazo", "binder": "archivador", "storage": "almacén", "other": "otro"}


def reorder_owned(location: int, card_ids: list[int]) -> None:
    """«Mi orden»: esas cartas, en ese orden, dentro de la ubicación."""
    with transaction.atomic():
        services.reorder_location(_location(location), card_ids)


def backup_document(entries: list[dict], exported_at: str, locations: list[dict] | None = None) -> dict:
    """Copia de seguridad de la colección: sus ubicaciones (también las vacías) y
    una fila por carta y ubicación, sin nada que sobre."""
    rows = sorted(entries, key=lambda e: (e["card_number"], e["bandai_id"], e.get("location", ""), bool(e.get("fake"))))
    cards = []
    for e in rows:
        row = {"id": e["bandai_id"], "number": e["card_number"], "name": e["name"],
               "qty": e["quantity"], "location": e.get("location", "")}
        if e.get("fake"):
            row["fake"] = True
        if e.get("notes"):
            row["notes"] = e["notes"]
        cards.append(row)
    places = []
    for loc in locations or []:
        place = {"name": loc["name"], "kind": KIND_NAMES.get(loc.get("kind"), loc.get("kind", "")),
                 "cards": loc.get("cards", 0), "copies": loc.get("copies", 0)}
        if loc.get("fakes"):
            place["fakes"] = loc["fakes"]
        if loc.get("notes"):
            place["notes"] = loc["notes"]
        places.append(place)
    return {
        "format": "dbs-collection",
        "version": 4,
        "exported_at": exported_at,
        "total_cards": len({e["bandai_id"] for e in rows}),
        "total_copies": sum(e["quantity"] for e in rows),
        "total_fakes": sum(e["quantity"] for e in rows if e.get("fake")),
        "locations": places,
        "cards": cards,
    }
