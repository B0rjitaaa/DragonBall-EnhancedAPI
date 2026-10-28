"""El precio de cada carta, combinando las fuentes, y su historial.

- A mano (revisión): manda siempre.
- Cardmarket con ventas (o confirmado en la revisión): es el precio, salvo que TCGplayer (ventas
  reales en EE. UU., en €) sea menos de la mitad: entonces TCGplayer (corrige precios inflados).
- Sin ventas en Cardmarket pero con TCGplayer: el menor de TCGplayer y el anuncio de Cardmarket (si no
  es dudoso): no vale más de lo que cuesta comprarla en Europa.
- Solo un anuncio en Cardmarket y nada en TCGplayer: ese anuncio, que no cuenta en el valor.
El historial (PricePoint) guarda el precio que cuenta, solo cuando cambia.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q

from cards.models import Card

from .models import CardmarketLink, CardPrice, ExchangeRate, PricePoint
from .tcgplayer import to_eur

# TCGplayer manda si es menos de esta parte del precio de Cardmarket.
TCG_FLOOR = Decimal("0.5")


def combine(link: CardmarketLink | None, tcg_eur: Decimal | None) -> tuple[Decimal, str, bool] | None:
    """(precio, fuente, cuenta en el valor) de una carta, o None si no hay ninguno."""
    if link is not None and link.manual_price is not None:
        return link.manual_price, CardPrice.Source.MANUAL, True
    product = link.product if link is not None else None
    cm = product.price if product is not None else None
    cm_sales = cm is not None and not link.suspect and (not product.price_is_low or link.method == link.Method.MANUAL)
    if cm_sales:
        if tcg_eur is not None and tcg_eur < cm * TCG_FLOOR:
            return tcg_eur, CardPrice.Source.TCGPLAYER, True
        return cm, CardPrice.Source.CARDMARKET, True
    if tcg_eur is not None:
        # Sin ventas en Cardmarket pero con un anuncio (no dudoso): si se puede comprar en Europa por
        # menos de lo que dice TCGplayer, ese anuncio (TCGplayer suele ir muy por encima en sets recientes).
        if cm is not None and not link.suspect and cm < tcg_eur:
            return cm, CardPrice.Source.CARDMARKET, True
        return tcg_eur, CardPrice.Source.TCGPLAYER, True
    if cm is not None:
        return cm, CardPrice.Source.CARDMARKET, False
    return None


def refresh(card_ids=None, today: date | None = None) -> int:
    """Recalcula el precio de las cartas (todas, o las indicadas) y apunta en el historial lo que cambie."""
    today = today or date.today()
    rate = ExchangeRate.latest()
    cards = Card.objects.filter(Q(cardmarket__isnull=False) | Q(tcgplayer__isnull=False))
    if card_ids is not None:
        cards = cards.filter(id__in=card_ids)
    cards = cards.select_related("cardmarket__product", "tcgplayer__product").only(
        "id", "cardmarket__method", "cardmarket__manual_price", "cardmarket__suspect", "cardmarket__product__price",
        "cardmarket__product__price_is_low", "tcgplayer__product__market_usd",
    )
    prices, gone = [], []
    for card in cards:
        link = getattr(card, "cardmarket", None)
        tcg = getattr(card, "tcgplayer", None)
        tcg_eur = to_eur(tcg.product.market_usd, rate) if tcg is not None else None
        result = combine(link, tcg_eur)
        if result is None:
            gone.append(card.id)
            continue
        eur, source, counts = result
        cm = link.product.price if link is not None and link.product is not None else None
        prices.append(CardPrice(card_id=card.id, eur=eur, source=source, counts=counts,
                                cardmarket_eur=cm, tcgplayer_eur=tcg_eur))
    with transaction.atomic():
        stale = CardPrice.objects.filter(card_id__in=gone) if card_ids is not None else \
            CardPrice.objects.exclude(card_id__in=[p.card_id for p in prices])
        stale.delete()
        CardPrice.objects.bulk_create(
            prices, batch_size=2000, update_conflicts=True, unique_fields=["card"],
            update_fields=["eur", "source", "counts", "cardmarket_eur", "tcgplayer_eur", "updated_at"],
        )
        _record_history([p for p in prices if p.counts], today)
    return len(prices)


def _record_history(prices: list[CardPrice], today: date) -> None:
    last = {}
    for card_id, eur in PricePoint.objects.filter(card_id__in=[p.card_id for p in prices]) \
            .order_by("card_id", "-date").distinct("card_id").values_list("card_id", "eur"):
        last[card_id] = eur
    PricePoint.objects.bulk_create(
        [PricePoint(card_id=p.card_id, date=today, eur=p.eur) for p in prices if last.get(p.card_id) != p.eur],
        batch_size=2000, update_conflicts=True, unique_fields=["card", "date"], update_fields=["eur"],
    )


def price_on(card_ids, day: date) -> dict[int, Decimal]:
    """El precio que tenía cada carta en una fecha (el último apuntado hasta ese día)."""
    return dict(
        PricePoint.objects.filter(card_id__in=card_ids, date__lte=day).order_by("card_id", "-date")
        .distinct("card_id").values_list("card_id", "eur")
    )


def change(card_id: int, days: int, today: date | None = None) -> float | None:
    """Variación (en tanto por uno) del precio de una carta en los últimos `days` días."""
    today = today or date.today()
    now = price_on([card_id], today).get(card_id)
    before = price_on([card_id], today - timedelta(days=days)).get(card_id)
    if now is None or before is None or before == 0:
        return None
    return float((now - before) / before)
