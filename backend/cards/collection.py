"""Mi colección vista desde el catálogo: copias por carta y su reparto por ubicación.

Las copias viven en la app `collection` (ubicaciones y filas de copias). Aquí se
consultan para el buscador, las facetas y las acciones de Mi colección: todo se
resuelve en la base de datos (qué cartas entran, orden y totales) y el reparto por
ubicaciones solo se lee para las cartas de la página que se muestra.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass

from django.db import transaction
from django.db.models import Min, OuterRef, Q, QuerySet, Subquery, Sum
from django.db.models.functions import Coalesce

from collection import services
from collection.models import CollectionEntry, Location

from .models import Card


class CollectionUnavailable(Exception):
    """Error de una acción de Mi colección, con el estado HTTP a devolver (y datos extra)."""

    def __init__(self, message: str, status: int, data: dict | None = None):
        super().__init__(message)
        self.status = status
        self.data = data or {}


@dataclass
class Scope:
    """Qué copias cuentan en Mi colección: todas o las de una ubicación, auténticas, con falsas o solo falsas.

    Una carta entra si tiene alguna fila de copias que cumpla todas las condiciones a la
    vez (p. ej. las falsas que están en esa ubicación).
    """

    location_id: int | None = None
    with_fakes: bool = False
    only_fakes: bool = False

    @property
    def entries(self) -> QuerySet:
        """Filas de copias que cuentan."""
        q = Q()
        if self.location_id is not None:
            q &= Q(location_id=self.location_id)
        if self.only_fakes:
            q &= Q(fake=True)
        elif not self.with_fakes:
            q &= Q(fake=False)
        return CollectionEntry.objects.filter(q)

    def card_ids(self) -> QuerySet:
        """Subconsulta con los ids de las cartas que entran (para Card.objects.filter(id__in=…))."""
        return self.entries.values("card_id")

    def _per_card(self, value: str, aggregate):
        return Subquery(
            self.entries.filter(card_id=OuterRef("id")).order_by().values("card_id")
            .annotate(v=aggregate(value)).values("v")[:1]
        )

    def with_quantity(self, cards: QuerySet) -> QuerySet:
        """Anota `owned_qty`: copias que cuentan de cada carta (para ordenar por copias)."""
        return cards.annotate(owned_qty=Coalesce(self._per_card("quantity", Sum), 0))

    def with_position(self, cards: QuerySet) -> QuerySet:
        """Anota `owned_pos`: posición de la carta en la ubicación («Mi orden»)."""
        return cards.annotate(owned_pos=Coalesce(self._per_card("position", Min), 0))

    def total_copies(self, cards: QuerySet) -> int:
        return self.entries.filter(card_id__in=cards.order_by().values("id")).aggregate(n=Sum("quantity"))["n"] or 0

    def fingerprint(self) -> str:
        """Cambia en cuanto cambian las copias que cuentan: clave de caché de las facetas."""
        rows = self.entries.order_by("card_id", "location_id", "fake").values_list("card_id", "quantity")
        return hashlib.sha1(repr(list(rows)).encode()).hexdigest()[:16]

    def details(self, card_ids) -> dict[int, dict]:
        """Por carta: copias que cuentan (`quantity`), en total (`total_quantity`), falsas y su
        reparto por ubicación (todas las filas, no solo las que cuentan)."""
        counted = dict(
            self.entries.filter(card_id__in=card_ids).order_by().values("card_id")
            .annotate(n=Sum("quantity")).values_list("card_id", "n")
        )
        out: dict[int, dict] = defaultdict(lambda: {"quantity": 0, "total_quantity": 0, "fakes": 0, "locations": []})
        for row in _rows(CollectionEntry.objects.filter(card_id__in=card_ids)):
            item = out[row["bandai_id"]]
            item["total_quantity"] += row["quantity"]
            item["fakes"] += row["quantity"] if row["fake"] else 0
            item["locations"].append({
                "id": row["location_id"],
                "name": row["location"],
                "kind": row["location_kind"],
                "quantity": row["quantity"],
                "fake": row["fake"],
                "position": row["position"],
                "notes": row["notes"],
            })
        for card_id, item in out.items():
            item["quantity"] = counted.get(card_id, 0)
        return dict(out)


_FIELDS = {
    "bandai_id": "card_id",
    "card_number": "card__card_number",
    "name": "card__name",
    "quantity": "quantity",
    "location_id": "location_id",
    "location": "location__name",
    "location_kind": "location__kind",
    "fake": "fake",
    "position": "position",
    "notes": "notes",
}


def _rows(entries: QuerySet) -> list[dict]:
    """Filas de copias con solo las columnas que se usan: la ficha completa de cada carta
    (respuesta de Bandai, textos…) pesa ~2 KB y aquí no hace falta."""
    entries = entries.order_by(
        "card__card_number", "card_id", "-location__is_default", "location__position", "location__name", "fake"
    )
    return [dict(zip(_FIELDS, values)) for values in entries.values_list(*_FIELDS.values())]


def fetch_export() -> list[dict]:
    """Una fila por carta, ubicación y autenticidad (la usa la copia de seguridad)."""
    return _rows(CollectionEntry.objects.all())


def _summary(card: Card) -> dict:
    result = services.card_summary(card)
    return {"quantity": result["quantity"], "fakes": result["fakes"], "locations": result["locations"]}


def _card(card_id: int) -> Card:
    card = Card.objects.filter(id=card_id).first()
    if card is None:
        raise CollectionUnavailable("Unknown card", 404)
    return card


def _location(location_id: int | None) -> Location | None:
    if location_id is None:
        return None
    location = Location.objects.filter(id=location_id).first()
    if location is None:
        raise CollectionUnavailable("Unknown location", 400, {"location": "Unknown location"})
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
        raise CollectionUnavailable("There are no copies of that card in that location", 404)
    return _summary(card)


KIND_NAMES = {"deck": "deck", "binder": "binder", "storage": "storage", "other": "other"}


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
