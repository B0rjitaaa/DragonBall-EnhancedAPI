"""Descarga del catálogo y la guía de precios públicos de Cardmarket (uno por juego, a diario).

https://news.cardmarket.com/en/Magic/were-making-the-price-guide-and-product-catalogue-available-for-download
Dragon Ball Super es el juego 13 (Masters y Fusion World juntos).
"""
from __future__ import annotations

import html
import logging
from datetime import datetime
from decimal import Decimal

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import CardmarketExpansion, CardmarketProduct

logger = logging.getLogger(__name__)

BASE = "https://downloads.s3.cardmarket.com/productCatalog"
PRICE_FIELDS = ("trend", "avg", "low", "avg1", "avg7", "avg30")
LOW_CAP = 5  # el precio nunca pasa de 5 veces el anuncio más barato


def is_fusion_world(name: str) -> bool:
    return "[Fusion World]" in name


def _get(url: str) -> dict:
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.json()


def fetch() -> tuple[list[dict], list[dict]]:
    """Catálogo de cartas sueltas y guía de precios del juego (CARDMARKET_GAME_ID)."""
    game = settings.CARDMARKET_GAME_ID
    products = _get(f"{BASE}/productList/products_singles_{game}.json")["products"]
    guides = _get(f"{BASE}/priceGuide/price_guide_{game}.json")["priceGuides"]
    return products, guides


def _decimal(value) -> Decimal | None:
    # 0 es "sin datos" (p. ej. trend de una carta recién salida).
    return Decimal(str(value)).quantize(Decimal("0.01")) if value else None


def reference_price(guide: dict) -> tuple[Decimal | None, bool]:
    """El precio de la carta y si es solo el anuncio más barato.

    Las medias de Cardmarket se disparan con ventas sueltas (y mezclan foil, idiomas y estados): el
    precio es el menor de el trend, la mediana de las medias de 1, 7 y 30 días y LOW_CAP veces el
    anuncio más barato. Sin ventas (sets recién salidos): el anuncio más barato, marcado.
    """
    averages = sorted(v for v in (_decimal(guide.get(f)) for f in ("avg1", "avg7", "avg30")) if v is not None)
    sales = [v for v in (_decimal(guide.get("trend")), averages[len(averages) // 2] if averages else None) if v is not None]
    low = _decimal(guide.get("low"))
    if not sales:
        return low, low is not None
    return min(sales + ([low * LOW_CAP] if low is not None else [])), False


def _date(value: str | None):
    try:
        return timezone.make_aware(datetime.strptime(value, "%Y-%m-%d %H:%M:%S")) if value else None
    except ValueError:
        return None


def store(products: list[dict], guides: list[dict]) -> int:
    """Guarda expansiones y productos con su precio del día. Devuelve cuántos productos."""
    now = timezone.now()
    by_id = {g["idProduct"]: g for g in guides}
    # Una expansión es de Fusion World si lo son la mayoría de sus cartas: alguna expansión de Masters
    # trae, por error de Cardmarket, una carta suelta de Fusion World (y esa se ignora al emparejar).
    counts: dict[int, list[int]] = {}
    rows = []
    for p in products:
        name = html.unescape(p["name"])
        total_fw = counts.setdefault(p["idExpansion"], [0, 0])
        total_fw[0] += 1
        total_fw[1] += is_fusion_world(name)
        guide = by_id.get(p["idProduct"], {})
        price, is_low = reference_price(guide)
        rows.append(CardmarketProduct(
            id=p["idProduct"], name=name[:255], expansion_id=p["idExpansion"], metacard=p.get("idMetacard"),
            date_added=_date(p.get("dateAdded")), price=price, price_is_low=is_low, fetched_at=now,
            **{f: _decimal(guide.get(f)) for f in PRICE_FIELDS},
        ))
    expansions = [CardmarketExpansion(id=exp_id, fusion_world=fw * 2 > total) for exp_id, (total, fw) in counts.items()]
    with transaction.atomic():
        CardmarketExpansion.objects.bulk_create(
            expansions, update_conflicts=True, unique_fields=["id"], update_fields=["fusion_world"]
        )
        CardmarketProduct.objects.bulk_create(
            rows, batch_size=2000, update_conflicts=True, unique_fields=["id"],
            update_fields=["name", "expansion", "metacard", "date_added", "price", "price_is_low", "fetched_at",
                           *PRICE_FIELDS],
        )
    return len(rows)
