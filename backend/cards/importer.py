"""Guarda cartas (ya descargadas) en la base de datos."""
from __future__ import annotations

import logging
from collections.abc import Iterable

from django.core.cache import cache
from django.db import transaction

from .models import Card
from .parsing import parse_card

logger = logging.getLogger(__name__)

FACETS_VERSION_KEY = "facets:version"
BATCH_SIZE = 500
UPDATE_FIELDS = [
    # legality* la gestiona banlist.apply_banlist(): no se pisa al reimportar
    f.name for f in Card._meta.concrete_fields if f.name not in {"id", "created_at", "legality", "legality_since"}
]


def upsert_cards(items: Iterable[dict]) -> tuple[int, int, list[int]]:
    """Inserta/actualiza cartas en bloque. Devuelve (creadas, actualizadas, ids_con_error)."""
    parsed: list[Card] = []
    errors: list[int] = []
    for data in items:
        try:
            parsed.append(Card(**parse_card(data)))
        except Exception:  # noqa: BLE001 - una carta rara no debe tumbar la importación
            logger.exception("No se pudo parsear la carta %s", data.get("id"))
            if data.get("id"):
                errors.append(int(data["id"]))

    ids = [c.id for c in parsed]
    existing = set(Card.objects.filter(id__in=ids).values_list("id", flat=True))

    with transaction.atomic():
        for start in range(0, len(parsed), BATCH_SIZE):
            Card.objects.bulk_create(
                parsed[start:start + BATCH_SIZE],
                update_conflicts=True,
                unique_fields=["id"],
                update_fields=UPDATE_FIELDS,
            )

    from .banlist import apply_banlist  # evitar import circular
    apply_banlist({c.card_number for c in parsed})
    invalidate_facets()
    created = len(set(ids) - existing)
    return created, len(ids) - created, errors


def invalidate_facets() -> None:
    """Las facetas cacheadas llevan la versión en la clave: subirla las invalida todas."""
    try:
        cache.incr(FACETS_VERSION_KEY)
    except ValueError:
        cache.set(FACETS_VERSION_KEY, 1, timeout=None)
