"""Empareja nuestras impresiones con los productos de Cardmarket.

El catálogo de Cardmarket no trae número ni rareza; solo nombre y expansión. Por eso:
1. Cada expansión de Cardmarket va al set nuestro con más nombres en común.
2. Dentro del set, por nombre ("cara // cara despertada" en los Leader) y por la pista que
   Cardmarket añade entre paréntesis a los nombres repetidos: número ("Vegeta (BT1-038)"),
   set ("Uub (BT11)") o color ("Son Goku (Green)").
3. Nuestras reimpresiones idénticas (mismo número y rareza) cuentan como una. Una carta y un
   producto: emparejados. Varias impresiones del mismo nombre (normal, SPR, GDR…) y tantos
   productos como impresiones: por orden de alta en las dos bases.
   Las promos y reimpresiones que no casan toman el producto de su versión normal ya emparejada
   (mismo número y rareza). Lo demás queda sin emparejar (para revisarlo a mano).
Los emparejamientos (también los «no está en Cardmarket») y las expansiones elegidos a mano
no se tocan; se eligen en la página de revisión (review.py).
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

from django.db import transaction

from cards.models import Card

from .cardmarket import is_fusion_world
from .models import CardmarketExpansion, CardmarketLink, CardmarketProduct

COLORS = {"red", "blue", "green", "yellow", "black", "white"}
MIN_EXPANSION_SCORE = 0.3
# Orden de las rarezas de una misma carta (de menos a más rara). Las demás (PR, ST, EX…) no se comparan.
RARITY_RANK = {r: i for i, r in enumerate("C UC R SR SPR SCR GDR".split())}
# Precio dudoso: solo un anuncio y por encima de lo que valen el 99 % de las cartas de su rareza con
# ventas (con al menos SUSPECT_MIN_SAMPLES para comparar; las GDR casi no tienen y no se marcan).
SUSPECT_PERCENTILE = 0.99
SUSPECT_MIN_SAMPLES = 20


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (text or "").lower().replace("&", "and"))


def norm_number(number: str) -> str:
    """BT06-048, BT6-48 y BT6-048 son el mismo número."""
    return re.sub(r"([A-Z]+)-?0*(\d+)-0*(\d+)", lambda m: f"{m[1]}{m[2]}-{int(m[3]):03d}", number.upper())


@dataclass(frozen=True)
class Parsed:
    front: str
    back: str
    hint: tuple[str, str] | None


def parse_name(name: str) -> Parsed:
    hint = None
    m = re.search(r"\s*\(([^)]*)\)\s*$", name)
    if m:
        h, name = m[1].strip(), name[:m.start()]
        if re.fullmatch(r"[A-Za-z]+-?\d+-\d+", h):
            hint = ("num", norm_number(h))
        elif h.lower() in COLORS:
            hint = ("color", h.capitalize())
        elif re.fullmatch(r"[A-Za-z]+-?\d+", h):
            hint = ("set", re.sub(r"^([A-Z]+)-?0*", r"\1", h.upper()))
        else:
            hint = ("other", h)
    front, _, back = name.partition(" // ")
    return Parsed(norm(front), norm(back), hint)


def fits(card: Card, parsed: Parsed) -> bool:
    if norm(card.name) != parsed.front:
        return False
    if parsed.back and norm(card.back_name) != parsed.back:
        return False
    kind, value = parsed.hint or (None, None)
    if kind == "num":
        return norm_number(card.card_number) == value
    if kind == "color":
        return value in (card.colors or [])
    if kind == "set":
        return card.set_code.replace("-", "") == value
    return True


def map_expansions(cards_by_set: dict[str, list[Card]]) -> int:
    """Cada expansión (no elegida a mano) al set nuestro con más nombres en común."""
    names_by_set = {s: {norm(c.name) for c in cs} for s, cs in cards_by_set.items()}
    products = defaultdict(set)
    for exp_id, name in CardmarketProduct.objects.filter(expansion__fusion_world=False).values_list("expansion_id", "name"):
        if not is_fusion_world(name):
            products[exp_id].add(parse_name(name).front)
    updated = []
    for exp in CardmarketExpansion.objects.filter(manual=False, fusion_world=False):
        names = products.get(exp.id, set())
        best = max(names_by_set, key=lambda s: len(names & names_by_set[s]), default="")
        score = len(names & names_by_set.get(best, set())) / len(names) if names else 0
        exp.card_set, exp.score = (best, score) if score >= MIN_EXPANSION_SCORE else ("", score)
        updated.append(exp)
    CardmarketExpansion.objects.bulk_update(updated, ["card_set", "score"])
    return sum(1 for e in updated if e.card_set)


def _pair(variants: list[list[Card]], products: list[CardmarketProduct]):
    """Empareja impresiones y productos. Con rarezas conocidas y distintas, la menos rara con el producto
    más barato (los que no tienen ventas, al final: suelen ser los alt-art); si no, por orden de alta."""
    ranks = [RARITY_RANK.get(v[0].rarity_code) for v in variants]
    if len(variants) > 1 and None not in ranks and len(set(ranks)) == len(ranks):
        by_price = sorted(products, key=lambda p: (p.price is None or p.price_is_low, p.price or 0, p.id))
        return zip(sorted(variants, key=lambda v: RARITY_RANK[v[0].rarity_code]), by_price)
    return zip(sorted(variants, key=lambda v: min(c.id for c in v)), sorted(products, key=lambda p: p.id))


def _mark_suspects(links: list[CardmarketLink]) -> int:
    """Marca los precios dudosos: solo anuncio y por encima del percentil 99 de su rareza con ventas."""
    sales = defaultdict(list)
    for link in links:
        if link.product and link.product.price is not None and not link.product.price_is_low:
            sales[link.card.rarity_code].append(link.product.price)
    ceilings = {}
    for rarity, prices in sales.items():
        if len(prices) >= SUSPECT_MIN_SAMPLES:
            prices.sort()
            ceilings[rarity] = prices[min(len(prices) - 1, int(len(prices) * SUSPECT_PERCENTILE))]
    for link in links:
        p = link.product
        ceiling = ceilings.get(link.card.rarity_code)
        link.suspect = bool(p and p.price_is_low and p.price is not None and ceiling is not None and p.price > ceiling)
    return sum(link.suspect for link in links)


def match_all() -> dict:
    """Rehace los emparejamientos automáticos. Devuelve cuántos de cada tipo."""
    cards_by_set: dict[str, list[Card]] = defaultdict(list)
    cards_by_code: dict[str, list[Card]] = defaultdict(list)
    for card in Card.objects.only("id", "name", "back_name", "card_number", "rarity_code", "colors", "set_code", "card_set"):
        cards_by_set[card.card_set].append(card)
        cards_by_code[card.set_code].append(card)
    mapped = map_expansions(cards_by_set)
    # Un set nuestro puede venir partido en varios card_set: si la carta no está en el de la
    # expansión, se busca en todo su set_code (BT19…).
    code_of = {s: cs[0].set_code for s, cs in cards_by_set.items() if cs}

    manual = CardmarketLink.objects.filter(method__in=CardmarketLink.MANUAL_METHODS)
    manual_cards = set(manual.values_list("card_id", flat=True))
    manual_products = set(manual.exclude(product=None).values_list("product_id", flat=True))
    # Por expansión de Cardmarket: varias pueden ir al mismo set nuestro (p. ej. el set y sus promos).
    groups: dict[tuple, list[CardmarketProduct]] = defaultdict(list)
    for product in CardmarketProduct.objects.filter(expansion__fusion_world=False).exclude(expansion__card_set="") \
            .exclude(name__contains="[Fusion World]") \
            .select_related("expansion").only("id", "name", "price", "price_is_low", "expansion__card_set", "expansion__score"):
        groups[(product.expansion, parse_name(product.name))].append(product)

    links: dict[int, tuple[float, CardmarketLink]] = {}
    for (expansion, parsed), products in groups.items():
        cards = [c for c in cards_by_set.get(expansion.card_set, []) if fits(c, parsed)] \
            or [c for c in cards_by_code.get(code_of.get(expansion.card_set), []) if fits(c, parsed)]
        # Si una parte del grupo se eligió a mano, lo que queda ya no se puede deducir: a revisar.
        if any(c.id in manual_cards for c in cards) or any(p.id in manual_products for p in products):
            continue
        # Reimpresiones idénticas (mismo número y rareza): una sola carta para Cardmarket. Salvo que
        # todas sean del mismo número y rareza y Cardmarket tenga un producto por impresión: alt-arts
        # (BT20-149 SCR V.1 y V.2), que van una a una por orden. Con rarezas mezcladas, no se deduce.
        variants: dict[tuple, list[Card]] = defaultdict(list)
        for card in cards:
            variants[(card.card_number, card.rarity_code)].append(card)
        if len(variants) == 1 and len(products) == len(cards) > 1:
            variants = {(card.id,): [card] for card in cards}
        if not variants or len(products) != len(variants):
            continue
        method = CardmarketLink.Method.AUTO if len(products) == 1 else CardmarketLink.Method.ORDERED
        for variant, product in _pair(list(variants.values()), products):
            for card in variant:
                # La misma carta en dos expansiones: gana la que más se parece a nuestro set (la principal).
                if card.id not in links or expansion.score > links[card.id][0]:
                    links[card.id] = (expansion.score, CardmarketLink(card=card, product=product, method=method))
    # Nombre único en los dos catálogos (una carta nuestra, salvo reimpresiones idénticas, y un producto):
    # son la misma aunque su expansión no se haya podido emparejar (p. ej. EX08).
    products_by_name: dict[str, list[CardmarketProduct]] = defaultdict(list)
    for (_, parsed), products in groups.items():
        products_by_name[parsed.front].extend(products)
    for product in CardmarketProduct.objects.filter(expansion__fusion_world=False, expansion__card_set="") \
            .exclude(name__contains="[Fusion World]").only("id", "name", "price", "price_is_low"):
        products_by_name[parse_name(product.name).front].append(product)
    prints_by_name: dict[str, dict[tuple, list[Card]]] = defaultdict(lambda: defaultdict(list))
    for cards in cards_by_set.values():
        for card in cards:
            prints_by_name[norm(card.name)][(card.card_number, card.rarity_code)].append(card)
    for name, prints in prints_by_name.items():
        products = products_by_name.get(name, [])
        if len(prints) != 1 or len(products) != 1:
            continue
        for card in next(iter(prints.values())):
            if card.id not in links and card.id not in manual_cards and products[0].id not in manual_products:
                links[card.id] = (0, CardmarketLink(card=card, product=products[0], method=CardmarketLink.Method.AUTO))

    # Promos y reimpresiones (Judge Pack, Card Game Fest, Starter Deck…): sin producto propio, toman el de su
    # versión normal ya emparejada (mismo número y rareza), como se venía eligiendo a mano en la revisión.
    regular = {(link.card.card_number, link.card.rarity_code): link.product for _, link in links.values()}
    for link in manual.exclude(product=None).select_related("card", "product"):
        regular.setdefault((link.card.card_number, link.card.rarity_code), link.product)
    for cards in cards_by_set.values():
        for card in cards:
            if card.id in links or card.id in manual_cards:
                continue
            product = regular.get((card.card_number, card.rarity_code))
            if product is not None:
                links[card.id] = (-1, CardmarketLink(card=card, product=product, method=CardmarketLink.Method.REPRINT))

    new = [link for _, link in links.values()]
    suspects = _mark_suspects(new)
    with transaction.atomic():
        CardmarketLink.objects.exclude(method__in=CardmarketLink.MANUAL_METHODS).delete()
        CardmarketLink.objects.bulk_create(new)
    return {
        "expansions": mapped,
        "auto": sum(1 for link in new if link.method == CardmarketLink.Method.AUTO),
        "ordered": sum(1 for link in new if link.method == CardmarketLink.Method.ORDERED),
        "reprint": sum(1 for link in new if link.method == CardmarketLink.Method.REPRINT),
        "suspect": suspects,
        "manual": len(manual_cards),
    }
