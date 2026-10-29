"""Volcado de los precios a un JSON (data/precios_dbs.json), para que una instalación nueva arranque ya
con precios, igual que con el catálogo (data/cartas_dbs.json).

Lleva todo lo de la app: productos y emparejamientos de Cardmarket y TCGplayer (también los elegidos a
mano en la revisión y los precios puestos a mano), el cambio del dólar, el precio de cada carta y su
historial. Se rehace solo tras cada descarga diaria de precios (tasks.sync_prices), así que el del
servidor siempre está al día; al cargarlo, la siguiente descarga diaria lo pone al día.
"""
from __future__ import annotations

import logging
from pathlib import Path

from django.core import serializers
from django.db import transaction
from django.utils import timezone

from cards.models import Card
from cards.seed import SEED_DIR, first_existing, read_json, write_json

from .models import (
    CardmarketExpansion, CardmarketLink, CardmarketProduct, CardPrice, ExchangeRate, PricePoint, TcgLink,
    TcgProduct,
)

logger = logging.getLogger(__name__)

FORMAT = "dbs-prices"
VERSION = 1
# En orden de dependencias: primero lo que otros apuntan.
MODELS = [
    ExchangeRate, CardmarketExpansion, CardmarketProduct, TcgProduct,
    CardmarketLink, TcgLink, CardPrice, PricePoint,
]
# Los que cuelgan de una carta: se saltan las de cartas que no estén en el catálogo.
BY_CARD = {CardmarketLink, TcgLink, CardPrice, PricePoint}


def export(path: str | Path) -> dict[str, int]:
    """Escribe el volcado en `path` (.gz: comprimido). Devuelve cuántas filas de cada tabla."""
    counts, rows = {}, []
    for model in MODELS:
        objects = serializers.serialize("python", model.objects.order_by("pk"))
        counts[model._meta.label] = len(objects)
        rows.extend(objects)
    write_json(path, {"format": FORMAT, "version": VERSION, "exported_at": timezone.now(), "counts": counts,
                      "objects": rows})
    return counts


def load(path: str | Path) -> dict[str, int]:
    """Carga un volcado sustituyendo los precios que hubiera. Devuelve cuántas filas de cada tabla."""
    doc = read_json(path)
    if doc.get("format") != FORMAT:
        raise ValueError(f"{path} is not a price dump ({FORMAT})")
    cards = set(Card.objects.values_list("id", flat=True))
    by_model: dict[type, list] = {model: [] for model in MODELS}
    for item in serializers.deserialize("python", doc["objects"]):
        obj = item.object
        if type(obj) in BY_CARD and obj.card_id not in cards:
            continue
        by_model[type(obj)].append(obj)
    with transaction.atomic():
        for model in reversed(MODELS):
            model.objects.all().delete()
        for model in MODELS:
            model.objects.bulk_create(by_model[model], batch_size=2000)
    return {model._meta.label: len(objs) for model, objs in by_model.items()}


def source_file() -> Path | None:
    """El volcado del que cargar los precios: el que rehace el servidor cada día (más reciente) o, si no
    está, el del repositorio (data/seed/)."""
    from django.conf import settings

    return first_existing(settings.PRICES_SNAPSHOT, SEED_DIR / "precios_dbs.json.gz")


def refresh_file(path: str | Path | None) -> None:
    """Rehace el volcado tras la descarga diaria. Si falla (disco, permisos), solo se apunta: los precios
    ya están guardados en la base de datos."""
    if not path:
        return
    try:
        counts = export(path)
        logger.info("Price dump written to %s: %s", path, counts)
    except OSError:
        logger.warning("Could not write the price dump to %s", path, exc_info=True)
