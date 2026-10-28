"""Radar de precios: lo que más sube y baja y lo más caro, de tu colección o de todo el catálogo."""
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Max, Min
from rest_framework.response import Response
from rest_framework.views import APIView

from cards.models import Card
from cards.serializers import CardListSerializer

from .models import CardPrice, PricePoint
from .pricing import price_on
from .services import PRICE_RELATED

TOP = 15
# Para subidas y bajadas, solo cartas que valen algo (de 0,02 € a 0,04 € es un +100 % sin interés).
MIN_EUR = Decimal("1")
PERIODS = (7, 30, 90)


def collection_value_series(days: int) -> dict:
    """Valor de tu colección (copias auténticas con precio que cuenta) cada día de los últimos `days` días,
    con los precios de cada día y las copias de hoy."""
    from collection.models import CollectionEntry

    qty = defaultdict(int)
    for card_id, n in CollectionEntry.objects.filter(fake=False, card__price__counts=True) \
            .values_list("card_id", "quantity"):
        qty[card_id] += n
    points = defaultdict(list)
    for card_id, day, eur in PricePoint.objects.filter(card_id__in=list(qty)).order_by("date") \
            .values_list("card_id", "date", "eur"):
        points[card_id].append((day, eur))
    today = date.today()
    series = []
    for offset in range(days, -1, -1):
        day = today - timedelta(days=offset)
        total = Decimal(0)
        for card_id, history in points.items():
            price = None
            for when, eur in history:
                if when > day:
                    break
                price = eur
            if price is not None:
                total += qty[card_id] * price
        series.append({"date": day.isoformat(), "eur": float(total)})
    now, first = series[-1]["eur"], next((p["eur"] for p in series if p["eur"]), 0)
    return {"series": series, "now": now, "change": (now - first) / first if first else None}


class RadarView(APIView):
    def get(self, request):
        days = int(request.query_params.get("days", 7))
        days = days if days in PERIODS else 7
        scope = "all" if request.query_params.get("scope") == "all" else "collection"
        prices = CardPrice.objects.filter(counts=True)
        if scope == "collection":
            prices = prices.filter(card__collection_entries__fake=False).distinct()
        current = dict(prices.values_list("card_id", "eur"))
        before = price_on(list(current), date.today() - timedelta(days=days))
        moves = [
            (card_id, eur, before[card_id], (eur - before[card_id]) / before[card_id])
            for card_id, eur in current.items()
            if before.get(card_id) and eur != before[card_id] and max(eur, before[card_id]) >= MIN_EUR
        ]
        risers = sorted((m for m in moves if m[3] > 0), key=lambda m: -m[3])[:TOP]
        fallers = sorted((m for m in moves if m[3] < 0), key=lambda m: m[3])[:TOP]
        expensive = sorted(current.items(), key=lambda kv: -kv[1])[:TOP]

        ids = {m[0] for m in risers + fallers} | {card_id for card_id, _ in expensive}
        cards = {c["id"]: c for c in CardListSerializer(
            Card.objects.filter(id__in=ids).select_related(*PRICE_RELATED), many=True).data}

        def row(card_id, old=None, pct=None):
            return {**cards[card_id], "before": float(old) if old is not None else None,
                    "change": float(pct) if pct is not None else None}

        span = PricePoint.objects.aggregate(first=Min("date"), last=Max("date"))
        return Response({
            "value": collection_value_series(days) if scope == "collection" else None,
            "days": days,
            "scope": scope,
            "since": span["first"],
            "updated": span["last"],
            "risers": [row(c, old, pct) for c, _, old, pct in risers],
            "fallers": [row(c, old, pct) for c, _, old, pct in fallers],
            "expensive": [row(c) for c, _ in expensive],
        })
