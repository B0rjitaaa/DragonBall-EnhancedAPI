"""Revisión a mano de los emparejamientos con Cardmarket (página del admin, ver admin.py).

- Tus cartas sin emparejar, con los productos de Cardmarket que se llaman igual.
- Los emparejamientos «por orden» dudosos: varias impresiones de una carta (normal, SPR,
  GDR…) donde una rareza mayor sale más barata que una menor.
- Los precios dudosos: solo un anuncio, muy caro para su rareza (no cuentan en el valor).
- Las cartas caras sin ventas: solo un anuncio, sin confirmar (no cuentan en el valor); a menudo,
  una edición rara (GDR) que el escáner confundió con la normal.
Solo cartas que tienes: el resto del catálogo no hace falta para el valor de la colección.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from django.db import transaction

from cards.models import Card

from . import pricing
from .matching import RARITY_RANK, norm, parse_name
from .models import CardmarketLink, CardmarketProduct

MAX_CANDIDATES = 12
# «Cartas caras sin ventas»: solo las de al menos este precio pedido (las baratas no cambian el valor).
LISTING_MIN_PRICE = 10


@dataclass
class Candidate:
    product: CardmarketProduct
    same_set: bool


@dataclass
class Pending:
    card: Card
    candidates: list[Candidate] = field(default_factory=list)


def _owned_cards():
    """Cartas de las que tienes copias auténticas: las falsas no cuentan en el valor, no hace falta precio."""
    return Card.objects.filter(collection_entries__fake=False).distinct()


def _products_by_name() -> dict[str, list[CardmarketProduct]]:
    by_name = defaultdict(list)
    for product in CardmarketProduct.objects.filter(expansion__fusion_world=False).exclude(name__contains="[Fusion World]") \
            .select_related("expansion"):
        by_name[parse_name(product.name).front].append(product)
    return by_name


def candidates(card: Card, by_name: dict[str, list[CardmarketProduct]]) -> list[Candidate]:
    """Productos que se llaman como la carta: primero los de su misma cara despertada y su set, y los más caros arriba."""
    products = by_name.get(norm(card.name), [])
    if not products:  # nombres escritos algo distinto: los que contienen el nombre o están contenidos en él
        key = norm(card.name)
        products = [p for name, ps in by_name.items() if len(name) > 5 and (key in name or name in key) for p in ps]
    found = [Candidate(p, p.expansion.card_set == card.card_set) for p in products]
    # Leaders: primero los de la misma cara despertada (hay productos con el mismo frente y otro reverso).
    back = norm(card.back_name)
    found.sort(key=lambda c: (bool(back) and parse_name(c.product.name).back != back, not c.same_set,
                              -(c.product.price or 0)))
    return found[:MAX_CANDIDATES]


def unmatched(limit: int, offset: int = 0) -> tuple[int, list[Pending]]:
    """Tus cartas sin emparejar (ni marcadas como «no está en Cardmarket»), con sus candidatos."""
    qs = _owned_cards().filter(cardmarket__isnull=True).order_by("set_code", "card_number", "id")
    total = qs.count()
    if not limit:
        return total, []
    by_name = _products_by_name()
    return total, [Pending(card, candidates(card, by_name)) for card in qs[offset:offset + limit]]


def suspects(limit: int, offset: int = 0) -> tuple[int, list[Pending]]:
    """Tus cartas con precio dudoso (solo un anuncio, muy caro para su rareza), con sus candidatos."""
    qs = _owned_cards().filter(cardmarket__suspect=True).select_related("cardmarket__product") \
        .order_by("set_code", "card_number", "id")
    total = qs.count()
    if not limit:
        return total, []
    by_name = _products_by_name()
    return total, [Pending(card, candidates(card, by_name)) for card in qs[offset:offset + limit]]


def listing_only(limit: int, offset: int = 0, min_price=LISTING_MIN_PRICE) -> tuple[int, list[Pending]]:
    """Tus cartas caras sin ventas (solo un anuncio, sin confirmar): no cuentan en el valor. Suelen ser
    ediciones raras (GDR, alt-art) que el escáner pudo confundir con la normal."""
    qs = _owned_cards().filter(price__counts=False, price__eur__gte=min_price, cardmarket__suspect=False) \
        .select_related("cardmarket__product").order_by("-price__eur", "card_number")
    total = qs.count()
    if not limit:
        return total, []
    by_name = _products_by_name()
    return total, [Pending(card, candidates(card, by_name)) for card in qs[offset:offset + limit]]


def other_prints(card: Card) -> list[Card]:
    """Las demás impresiones de la carta (mismo número): para «tengo otra edición»."""
    return list(Card.objects.filter(card_number=card.card_number).exclude(id=card.id)
                .select_related("price").order_by("id"))


def change_print(card: Card, target: Card) -> int:
    """Tus copias de `card` son en realidad de otra edición (`target`): pasan a ella en su misma ubicación,
    con sus notas y si son falsas; sus escaneos apuntan a la nueva. Devuelve cuántas copias."""
    from collection.models import CollectionEntry
    from collection.services import _take, add_copies
    from scanner.models import Scan

    moved = 0
    with transaction.atomic():
        for entry in CollectionEntry.objects.select_for_update().filter(card=card).select_related("location"):
            new = add_copies(target, entry.location, entry.quantity, entry.notes, fake=entry.fake)
            Scan.objects.filter(collection_entry=entry).update(collection_entry=new, matched_card=target)
            moved += entry.quantity
            _take(entry, entry.quantity)
    return moved


def doubtful() -> list[list[CardmarketLink]]:
    """Grupos «por orden» de tus cartas donde la rareza y el precio no van en el mismo orden."""
    owned = set(_owned_cards().values_list("id", flat=True))
    links = CardmarketLink.objects.filter(method=CardmarketLink.Method.ORDERED) \
        .select_related("card", "product", "product__expansion")
    groups = defaultdict(list)
    for link in links:
        groups[(link.product.expansion_id, parse_name(link.product.name))].append(link)
    out = []
    for group in groups.values():
        if not any(link.card_id in owned for link in group):
            continue
        ranked = [(RARITY_RANK[link.card.rarity_code], link.product.price) for link in group
                  if link.card.rarity_code in RARITY_RANK and link.product.price is not None]
        by_rarity = [price for _, price in sorted(ranked, key=lambda x: x[0])]
        if len({r for r, _ in ranked}) > 1 and by_rarity != sorted(by_rarity):
            out.append(sorted(group, key=lambda link: (RARITY_RANK.get(link.card.rarity_code, 99), link.card_id)))
    return sorted(out, key=lambda g: (g[0].card.set_code, g[0].card.card_number))


def _same_print(card: Card) -> list[int]:
    """La carta y sus reimpresiones idénticas (mismo número, rareza y set): llevan el mismo producto.
    Solo del mismo set: la versión normal de una promo (otro set) tiene su propio emparejamiento."""
    return list(Card.objects.filter(card_number=card.card_number, rarity_code=card.rarity_code, card_set=card.card_set)
                .values_list("id", flat=True))


def choose(card: Card, product: CardmarketProduct | None) -> int:
    """Fija a mano el producto de una carta (None: no está en Cardmarket). Devuelve cuántas impresiones."""
    method = CardmarketLink.Method.MANUAL if product else CardmarketLink.Method.NONE
    ids = _same_print(card)
    with transaction.atomic():
        for card_id in ids:
            CardmarketLink.objects.update_or_create(
                card_id=card_id, defaults={"product": product, "method": method, "manual_price": None, "suspect": False}
            )
    pricing.refresh(ids)
    return len(ids)


def set_price(card: Card, price) -> int:
    """Pone el precio a mano (cuando ningún producto de Cardmarket es el bueno). Devuelve cuántas impresiones."""
    ids = _same_print(card)
    with transaction.atomic():
        for card_id in ids:
            CardmarketLink.objects.update_or_create(
                card_id=card_id,
                defaults={"product": None, "method": CardmarketLink.Method.PRICE, "manual_price": price, "suspect": False},
            )
    pricing.refresh(ids)
    return len(ids)


def mark_fake(card: Card) -> int:
    """Tus copias auténticas de esta impresión son falsas: pasan a falsas en su misma ubicación
    (con sus notas). Devuelve cuántas copias."""
    from collection.models import CollectionEntry
    from collection.services import move_copies

    moved = 0
    with transaction.atomic():
        for entry in CollectionEntry.objects.filter(card=card, fake=False).select_related("location"):
            move_copies(card, entry.location, entry.location, entry.quantity, source_fake=False, target_fake=True)
            moved += entry.quantity
    return moved


def confirm(card_ids: list[int]) -> int:
    """Da por buenos unos emparejamientos automáticos: pasan a «elegido a mano»."""
    n = CardmarketLink.objects.filter(card_id__in=card_ids).exclude(product=None) \
        .update(method=CardmarketLink.Method.MANUAL)
    pricing.refresh(card_ids)
    return n
