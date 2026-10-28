"""Precio de una carta para la web y valor de lo que tienes (solo copias auténticas).

El precio sale de CardPrice (ver pricing.py), que combina Cardmarket, TCGplayer y lo puesto a mano.
"""
from __future__ import annotations

from urllib.parse import quote_plus

from django.db.models import DecimalField, F, QuerySet, Sum
from django.db.models.functions import Coalesce

from .models import CardPrice

# La carta en Cardmarket: con las ofertas de toda Europa (de donde salen los precios de la guía) y
# solo las de vendedores de España (país 10), que suelen ser menos y más caras.
# Solo cartas en inglés (idioma 1): la guía de precios mezcla idiomas, pero las ofertas se pueden filtrar.
PRODUCT_URL = "https://www.cardmarket.com/en/DragonBallSuper/Products?idProduct={id}&language=1"
SPAIN = "&sellerCountry=10"
# Sin producto en Cardmarket: la búsqueda por nombre.
SEARCH_URL = "https://www.cardmarket.com/en/DragonBallSuper/Products/Search?searchString={q}&language=1"
TCG_URL = "https://www.tcgplayer.com/product/{id}"
# Lo que se precarga para card_price (select_related).
PRICE_RELATED = ("price", "cardmarket__product", "tcgplayer__product")


def _related(card, name):
    try:
        return getattr(card, name)
    except Exception:  # noqa: BLE001 - RelatedObjectDoesNotExist de cada relación
        return None


def _f(value):
    return float(value) if value else None


def card_price(card, changes: bool = False) -> dict | None:
    """El precio de una carta para la web (mejor con select_related(*PRICE_RELATED)). Con `changes`,
    también su variación a 7 y 30 días (consulta el historial: solo en el detalle)."""
    price: CardPrice | None = _related(card, "price")
    if price is None:
        return None
    link = _related(card, "cardmarket")
    product = link.product if link is not None else None
    tcg = _related(card, "tcgplayer")
    search = SEARCH_URL.format(q=quote_plus(card.name))
    info = {
        "eur": float(price.eur),
        "source": price.source,
        "counts": price.counts,
        "manual": price.source == CardPrice.Source.MANUAL,
        # Sin ventas en ninguna fuente: solo lo que pide un vendedor en Cardmarket.
        "is_low": not price.counts,
        "suspect": bool(link and link.suspect),
        "cardmarket_eur": _f(price.cardmarket_eur),
        "tcgplayer_eur": _f(price.tcgplayer_eur),
        "trend": _f(product.trend) if product else None,
        "avg30": _f(product.avg30) if product else None,
        "low": _f(product.low) if product else None,
        "url": PRODUCT_URL.format(id=product.id) if product else search,
        "url_es": (PRODUCT_URL.format(id=product.id) if product else search) + SPAIN,
        "tcg_url": TCG_URL.format(id=tcg.product_id) if tcg else None,
    }
    if changes:
        from .pricing import change

        info["change_7"] = change(card.id, 7)
        info["change_30"] = change(card.id, 30)
    return info


MONEY = DecimalField(max_digits=12, decimal_places=2)


def _sum_value(entries: QuerySet):
    return entries.aggregate(
        v=Coalesce(Sum(F("quantity") * F("card__price__eur"), output_field=MONEY), 0, output_field=MONEY)
    )["v"]


def value_of(entries: QuerySet) -> dict:
    """Valor de unas filas de copias (sin las falsas): lo que tiene ventas o precio confirmado o a mano. Las
    cartas sin ventas (solo un anuncio) van aparte en `value_listing`, y las que no tienen precio se cuentan."""
    authentic = entries.filter(fake=False)
    priced = authentic.filter(card__price__counts=True)
    # Los dudosos (un anuncio absurdo, p. ej. 9.999 €) no suman ni aparte: hasta revisarlos, sin precio.
    listing = authentic.filter(card__price__counts=False).exclude(card__cardmarket__suspect=True)
    copies = authentic.aggregate(n=Sum("quantity"))["n"] or 0
    with_price = priced.aggregate(n=Sum("quantity"))["n"] or 0
    listing_copies = listing.aggregate(n=Sum("quantity"))["n"] or 0
    return {"value": float(_sum_value(priced)), "value_listing": float(_sum_value(listing)),
            "copies_priced": with_price, "copies_listing": listing_copies,
            "copies_unpriced": copies - with_price - listing_copies}


def values_by_location() -> dict[int, float]:
    """Valor de las copias auténticas de cada ubicación."""
    from collection.models import CollectionEntry

    rows = (
        CollectionEntry.objects.filter(fake=False, card__price__counts=True)
        .values("location_id")
        .annotate(v=Sum(F("quantity") * F("card__price__eur"), output_field=MONEY))
    )
    return {r["location_id"]: float(r["v"]) for r in rows}
