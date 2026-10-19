"""Mi colección: la colección escaneada en DragonBall-CameraCardChecker.

Se lee de su endpoint /api/collection/export/ (CARD_CHECKER_URL) y se agrega
por id de Bandai, la clave común de los dos proyectos (aquí, Card.id).
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache

CACHE_KEY = "my-collection:owned"
# Una interacción del buscador lanza varias peticiones (búsqueda + facetas):
# se reutiliza la colección unos segundos en vez de pedirla en cada una.
CACHE_TTL = 10


class CollectionUnavailable(Exception):
    def __init__(self, message: str, status: int):
        super().__init__(message)
        self.status = status


@dataclass
class Owned:
    cards: dict[int, dict] = field(default_factory=dict)  # id -> {quantity, conditions}
    numbers: dict[int, str] = field(default_factory=dict)  # id -> número de carta (para "missing")

    @property
    def ids(self) -> list[int]:
        return list(self.cards)

    @property
    def fingerprint(self) -> str:
        """Cambia en cuanto cambia la colección: sirve de clave de caché."""
        raw = json.dumps(sorted((i, c["quantity"]) for i, c in self.cards.items()))
        return hashlib.sha1(raw.encode()).hexdigest()[:16]

    def quantity(self, card_id: int) -> int:
        return self.cards.get(card_id, {}).get("quantity", 0)


def fetch_owned() -> Owned:
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached
    base = settings.CARD_CHECKER_URL.rstrip("/")
    if not base:
        raise CollectionUnavailable("CARD_CHECKER_URL no está configurado", 503)
    try:
        with urlopen(f"{base}/api/collection/export/", timeout=5) as resp:  # noqa: S310 - URL de configuración
            entries = json.load(resp)
    except (URLError, TimeoutError, ValueError) as exc:
        raise CollectionUnavailable(f"No se pudo leer la colección del escáner ({base}): {exc}", 502) from exc

    cards: dict[int, dict] = defaultdict(lambda: {"quantity": 0, "conditions": {}})
    numbers: dict[int, str] = {}
    for entry in entries:
        item = cards[entry["bandai_id"]]
        item["quantity"] += entry["quantity"]
        item["conditions"][entry["condition"]] = item["conditions"].get(entry["condition"], 0) + entry["quantity"]
        numbers[entry["bandai_id"]] = entry["card_number"]
    owned = Owned(dict(cards), numbers)
    cache.set(CACHE_KEY, owned, CACHE_TTL)
    return owned


def adjust_owned(card_id: int, delta: int) -> dict:
    """Suma o resta copias de una carta en la colección del escáner.

    Devuelve {quantity, conditions} tras el cambio y descarta la colección
    cacheada para que búsqueda y facetas reflejen el cambio al momento.
    """
    base = settings.CARD_CHECKER_URL.rstrip("/")
    if not base:
        raise CollectionUnavailable("CARD_CHECKER_URL no está configurado", 503)
    body = json.dumps({"bandai_id": card_id, "delta": delta}).encode()
    req = Request(f"{base}/api/collection/adjust/", data=body, method="POST",
                  headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=5) as resp:  # noqa: S310 - URL de configuración
            result = json.load(resp)
    except HTTPError as exc:
        detail = "la carta no está en el catálogo del escáner" if exc.code == 404 else f"HTTP {exc.code}"
        raise CollectionUnavailable(f"El escáner rechazó el cambio: {detail}", 502) from exc
    except (URLError, TimeoutError, ValueError) as exc:
        raise CollectionUnavailable(f"No se pudo hablar con el escáner ({base}): {exc}", 502) from exc
    cache.delete(CACHE_KEY)
    return {"quantity": result["quantity"], "conditions": result["conditions"]}
