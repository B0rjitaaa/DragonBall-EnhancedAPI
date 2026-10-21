"""Impresiones que Bandai no publica (promos de Event Pack, premios…).

Se crean clonando el registro de Bandai de la misma carta: mismo número,
texto y atributos, con su propia imagen y edición. Llevan un id fuera del
rango de Bandai, así que la sincronización nunca las pisa ni las borra, y
se exportan al escáner como cualquier otra carta.
"""
from __future__ import annotations

import copy

from .importer import upsert_cards
from .models import Card

# Los ids de Bandai TCG+ van por las decenas de miles: muy por debajo.
CUSTOM_ID_START = 900_000_000


def is_custom(card_id: int) -> bool:
    return card_id >= CUSTOM_ID_START


def add_printing(base: Card, image_url: str, card_set: str, card_id: int | None = None) -> Card:
    """Crea (o actualiza) una impresión propia de `base`. Devuelve la carta."""
    if card_id is None:
        last = Card.objects.filter(id__gte=CUSTOM_ID_START).order_by("-id").values_list("id", flat=True).first()
        card_id = (last or CUSTOM_ID_START) + 1
    elif not is_custom(card_id):
        raise ValueError(f"El id de una impresión propia debe ser >= {CUSTOM_ID_START}")

    raw = copy.deepcopy(base.raw)
    raw.update({
        "id": card_id,
        "image_url": image_url,
        "card_set": card_set,
        "custom_printing_of": base.id,
    })
    # Sin cara trasera propia: la de Bandai apuntaría a la imagen de otra impresión.
    for key in ("backcard_id", "backcard_image_url"):
        raw.pop(key, None)
    upsert_cards([raw])
    return Card.objects.get(id=card_id)
