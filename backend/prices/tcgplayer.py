"""Precios de TCGplayer (mercado de EE. UU., de ventas reales) vía tcgcsv.com, y su emparejamiento.

Normas de tcgcsv (https://tcgcsv.com/docs#usage-guidelines): una sincronización al día como mucho,
mirando antes last-updated.txt; User-Agent propio; 100 ms entre peticiones. Dragon Ball Super
(Masters) es la categoría 27: ~107 sets, ~214 peticiones.

El catálogo de TCGplayer trae número y rareza ("BT20-149", "Secret Rare") y marca las variantes al
final del nombre: "(Alternate Art)", "(SPR)", "(Silver Foil)", "(Gold-Stamped)"…
"""
from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import date
from decimal import Decimal

import requests
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from cards.models import Card

from .matching import norm_number
from .models import ExchangeRate, TcgLink, TcgProduct

BASE = "https://tcgcsv.com"
HEADERS = {"User-Agent": "DragonBallEnhancedAPI/1.0"}
PAUSE = 0.1
LAST_BUILD_KEY = "tcgcsv-last-build"
ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
# Variantes que son la misma carta que la normal con otra rareza en el nombre (no otra impresión).
RARITY_TAGS = {"SPR", "SLR", "SCR", "GDR", "DBR", "CR"}
# Variantes de arte alternativo: la segunda impresión de un mismo número y rareza.
ALT_ART = {"alternate art"}


def _get(path: str):
    time.sleep(PAUSE)
    response = requests.get(f"{BASE}{path}", headers=HEADERS, timeout=60)
    response.raise_for_status()
    return response.json() if path.endswith(("groups", "products", "prices")) else response.text


def _decimal(value) -> Decimal | None:
    return Decimal(str(value)).quantize(Decimal("0.01")) if value else None


def fetch_rate() -> ExchangeRate:
    """Cambio del dólar del BCE (un valor al día laborable)."""
    response = requests.get(ECB_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()
    root = ET.fromstring(response.content)
    for cube in root.iter():
        if cube.get("currency") == "USD":
            day = next(c.get("time") for c in root.iter() if c.get("time"))
            rate, _ = ExchangeRate.objects.update_or_create(
                date=date.fromisoformat(day), defaults={"usd_per_eur": Decimal(cube.get("rate"))}
            )
            return rate
    raise ValueError("El BCE no trae el cambio del dólar")


def parse(product: dict) -> dict:
    ext = {e["name"]: e["value"] for e in product.get("extendedData", [])}
    name = product["name"]
    m = re.search(r"\s*\(([^)]*)\)\s*$", name)
    number = (ext.get("Number") or "").split(" ")[0]
    return {
        "name": name[:255],
        "number": norm_number(number) if number else "",
        "rarity": (ext.get("Rarity") or "")[:64],
        "variant": (m[1] if m else "")[:64],
    }


def _best_price(prices: list[dict]) -> dict:
    """La versión Normal si tiene precio de mercado; si no, la Foil."""
    for sub in ("Normal", "Foil"):
        for p in prices:
            if p["subTypeName"] == sub and p.get("marketPrice"):
                return p
    return prices[0] if prices else {}


def sync(force: bool = False) -> int | None:
    """Descarga catálogo y precios de todos los sets (si tcgcsv tiene datos nuevos). Devuelve cuántos productos."""
    category = settings.TCGPLAYER_CATEGORY_ID
    build = _get("/last-updated.txt").strip()
    if not force and cache.get(LAST_BUILD_KEY) == build and TcgProduct.objects.exists():
        return None
    now = timezone.now()
    rows = []
    for group in _get(f"/tcgplayer/{category}/groups")["results"]:
        gid = group["groupId"]
        prices = defaultdict(list)
        for p in _get(f"/tcgplayer/{category}/{gid}/prices")["results"]:
            prices[p["productId"]].append(p)
        for product in _get(f"/tcgplayer/{category}/{gid}/products")["results"]:
            best = _best_price(prices.get(product["productId"], []))
            rows.append(TcgProduct(
                id=product["productId"], group_id=gid, group_name=group["name"][:255], **parse(product),
                market_usd=_decimal(best.get("marketPrice")), low_usd=_decimal(best.get("lowPrice")),
                sub_type=best.get("subTypeName", "")[:16], fetched_at=now,
            ))
    with transaction.atomic():
        TcgProduct.objects.bulk_create(
            rows, batch_size=2000, update_conflicts=True, unique_fields=["id"],
            update_fields=["group_id", "group_name", "name", "number", "rarity", "variant", "market_usd",
                           "low_usd", "sub_type", "fetched_at"],
        )
    cache.set(LAST_BUILD_KEY, build, None)
    return len(rows)


def _prefix(number: str) -> str:
    """El código del set de un número: BT11-032 → BT11, EX06-27 → EX6, P-003 → P."""
    m = re.match(r"([A-Z]+)0*(\d*)", number)
    return f"{m[1]}{m[2]}" if m else ""


def _rarity(name: str) -> str:
    return re.sub(r"s$", "", name.strip().lower())  # "Infinite Saiyan Rares" = "Infinite Saiyan Rare"


def _is_base(variant: str) -> bool:
    """La versión normal: sin variante, con la rareza en el nombre ("(SPR)") o con el año ("(2017)")."""
    return not variant or variant in RARITY_TAGS or bool(re.fullmatch(r"\d{4}", variant))


def match_all() -> int:
    """Empareja por número y rareza. Si la carta está en varios sets de TCGplayer (reimpresiones en
    otras cajas), se queda con la de su set de origen (donde predomina su código, primera edición).
    Con dos impresiones nuestras del mismo número y rareza, la segunda es el arte alternativo."""
    all_products = list(TcgProduct.objects.exclude(number="").only("id", "number", "rarity", "variant", "group_id", "group_name"))
    # Set de origen de cada código: el grupo donde ese código es mayoría (BT1 → Galactic Battle).
    per_group = defaultdict(lambda: defaultdict(int))
    for p in all_products:
        per_group[p.group_id][_prefix(p.number)] += 1
    home = {}
    for group_id, counts in per_group.items():
        prefix, n = max(counts.items(), key=lambda kv: kv[1])
        if n >= 0.6 * sum(counts.values()):
            home.setdefault(prefix, set()).add(group_id)

    products = defaultdict(lambda: {"base": [], "alt": []})
    for p in all_products:
        kind = "base" if _is_base(p.variant) else "alt" if p.variant.lower() in ALT_ART else None
        if kind:
            products[(p.number, _rarity(p.rarity))][kind].append(p)

    def pick(candidates: list[TcgProduct], prefix: str) -> TcgProduct | None:
        if len(candidates) == 1:
            return candidates[0]
        origin = [p for p in candidates if p.group_id in home.get(prefix, ()) and "pre-release" not in p.group_name.lower()]
        return min(origin, key=lambda p: (p.group_id, p.id)) if origin else None

    prints = defaultdict(list)
    for card in Card.objects.only("id", "card_number", "rarity"):
        prints[(norm_number(card.card_number), _rarity(card.rarity))].append(card)

    links = []
    for (number, rarity), cards in prints.items():
        found = products.get((number, rarity))
        base = pick(found["base"], _prefix(number)) if found else None
        if base is None:
            continue
        cards.sort(key=lambda c: c.id)
        links.append(TcgLink(card=cards[0], product=base))
        alt = pick(found["alt"], _prefix(number)) if found["alt"] else None
        if len(cards) == 2 and alt is not None:
            links.append(TcgLink(card=cards[1], product=alt))
        elif len(cards) > 1 and not found["alt"]:
            # Reimpresiones idénticas (sin arte alternativo en TCGplayer): el mismo producto.
            links.extend(TcgLink(card=c, product=base) for c in cards[1:])
    with transaction.atomic():
        TcgLink.objects.all().delete()
        TcgLink.objects.bulk_create(links)
    return len(links)


def to_eur(usd: Decimal | None, rate: ExchangeRate | None) -> Decimal | None:
    if usd is None or rate is None:
        return None
    return (usd / rate.usd_per_eur).quantize(Decimal("0.01"))

