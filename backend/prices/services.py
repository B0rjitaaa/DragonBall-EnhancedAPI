"""Precio de una carta y valor de lo que tienes (solo copias auténticas)."""
from __future__ import annotations

from urllib.parse import quote_plus

from django.db.models import DecimalField, F, Q, QuerySet, Sum
from django.db.models.functions import Coalesce

from .models import CardmarketProduct

# La carta en Cardmarket: con las ofertas de toda Europa (de donde salen los precios de la guía) y
# solo las de vendedores de España (país 10), que suelen ser menos y más caras.
# Solo cartas en inglés (idioma 1): la guía de precios mezcla idiomas, pero las ofertas se pueden filtrar.
PRODUCT_URL = "https://www.cardmarket.com/en/DragonBallSuper/Products?idProduct={id}&language=1"
SPAIN = "&sellerCountry=10"
# Sin producto (precio puesto a mano): la búsqueda por nombre.
SEARCH_URL = "https://www.cardmarket.com/en/DragonBallSuper/Products/Search?searchString={q}&language=1"


def price_info(product: CardmarketProduct | None) -> dict | None:
    """El precio de una carta para la web (None: sin emparejar o sin datos en Cardmarket)."""
    if product is None or product.price is None:
        return None
    return {
        "eur": float(product.price),
        "is_low": product.price_is_low,
        "trend": float(product.trend) if product.trend else None,
        "avg30": float(product.avg30) if product.avg30 else None,
        "low": float(product.low) if product.low else None,
        "manual": False,
        "url": PRODUCT_URL.format(id=product.id),
        "url_es": PRODUCT_URL.format(id=product.id) + SPAIN,
    }


def card_price(card) -> dict | None:
    """Precio de una carta (usa card.cardmarket, mejor con select_related("cardmarket__product"))."""
    try:
        link = card.cardmarket
    except type(card).cardmarket.RelatedObjectDoesNotExist:
        return None
    if link.manual_price is not None:
        search = SEARCH_URL.format(q=quote_plus(card.name))
        return {"eur": float(link.manual_price), "is_low": False, "manual": True, "suspect": False, "trend": None, "avg30": None,
                "low": None, "url": search, "url_es": search + SPAIN}
    info = price_info(link.product)
    if info is not None:
        info["suspect"] = link.suspect
    return info


# Precio de una fila de copias: el puesto a mano o, si no, el de su producto de Cardmarket.
PRICE = Coalesce("card__cardmarket__manual_price", "card__cardmarket__product__price")
# Los precios dudosos (ver matching._mark_suspects) no cuentan hasta revisarlos.
HAS_PRICE = Q(card__cardmarket__manual_price__isnull=False) | Q(
    card__cardmarket__product__price__isnull=False, card__cardmarket__suspect=False
)
MONEY = DecimalField(max_digits=12, decimal_places=2)


def _sum_value(entries: QuerySet):
    return entries.aggregate(v=Coalesce(Sum(F("quantity") * PRICE, output_field=MONEY), 0, output_field=MONEY))["v"]


def value_of(entries: QuerySet) -> dict:
    """Valor de unas filas de copias: las falsas no cuentan, y las que no tienen precio se cuentan aparte."""
    authentic = entries.filter(fake=False)
    priced = authentic.filter(HAS_PRICE)
    value = _sum_value(priced)
    # Parte del valor que es solo el anuncio más barato (cartas sin ventas): se indica aparte.
    low = _sum_value(priced.filter(card__cardmarket__manual_price__isnull=True,
                                   card__cardmarket__product__price_is_low=True))
    copies = authentic.aggregate(n=Sum("quantity"))["n"] or 0
    with_price = priced.aggregate(n=Sum("quantity"))["n"] or 0
    return {"value": float(value), "value_low": float(low), "copies_priced": with_price,
            "copies_unpriced": copies - with_price}


def values_by_location() -> dict[int, float]:
    """Valor de las copias auténticas de cada ubicación."""
    from collection.models import CollectionEntry

    rows = (
        CollectionEntry.objects.filter(HAS_PRICE, fake=False)
        .values("location_id")
        .annotate(v=Sum(F("quantity") * PRICE, output_field=MONEY))
    )
    return {r["location_id"]: float(r["v"]) for r in rows}
