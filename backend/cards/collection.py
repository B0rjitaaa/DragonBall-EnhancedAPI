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
    def __init__(self, message: str, status: int, data: dict | None = None):
        super().__init__(message)
        self.status = status
        self.data = data or {}


@dataclass
class Owned:
    # id -> {quantity, fakes, locations: [{id, name, kind, quantity, fake, notes}]}
    cards: dict[int, dict] = field(default_factory=dict)
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

    def filtered(self, keep) -> "Owned":
        """Solo las cartas con alguna fila de copias que cumpla `keep`; `quantity` pasa a ser las de esas filas."""
        cards = {}
        for card_id, item in self.cards.items():
            here = sum(loc["quantity"] for loc in item["locations"] if keep(loc))
            if here:
                cards[card_id] = {**item, "quantity": here, "total_quantity": item.get("total_quantity", item["quantity"])}
        return Owned(cards, {i: n for i, n in self.numbers.items() if i in cards})


def _base() -> str:
    base = settings.CARD_CHECKER_URL.rstrip("/")
    if not base:
        raise CollectionUnavailable("CARD_CHECKER_URL no está configurado", 503)
    return base


def checker_request(method: str, path: str, body: dict | None = None):
    """Llama a la API del escáner. Errores → CollectionUnavailable con el estado a devolver."""
    base = _base()
    data = json.dumps(body).encode() if body is not None else None
    req = Request(f"{base}{path}", data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=5) as resp:  # noqa: S310 - URL de configuración
            raw = resp.read()
            return json.loads(raw) if raw else None
    except HTTPError as exc:
        try:
            payload = json.loads(exc.read() or b"{}")
        except ValueError:
            payload = {}
        if exc.code in (400, 404, 409):
            # Errores del usuario (validación, conflicto…): se devuelven tal cual.
            detail = payload.get("detail") if isinstance(payload, dict) else None
            if exc.code == 404 and not detail:
                detail = "No encontrado en el escáner"
            raise CollectionUnavailable(detail or json.dumps(payload, ensure_ascii=False), exc.code, payload) from exc
        raise CollectionUnavailable(f"El escáner respondió HTTP {exc.code}", 502) from exc
    except (URLError, TimeoutError, ValueError) as exc:
        raise CollectionUnavailable(f"No se pudo hablar con el escáner ({base}): {exc}", 502) from exc


def fetch_export() -> list[dict]:
    """Entradas de la colección tal cual las da el escáner (una por carta y ubicación)."""
    base = _base()
    try:
        with urlopen(f"{base}/api/collection/export/", timeout=5) as resp:  # noqa: S310 - URL de configuración
            return json.load(resp)
    except (URLError, TimeoutError, ValueError) as exc:
        raise CollectionUnavailable(f"No se pudo leer la colección del escáner ({base}): {exc}", 502) from exc


def fetch_owned() -> Owned:
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached
    entries = fetch_export()

    cards: dict[int, dict] = defaultdict(lambda: {"quantity": 0, "fakes": 0, "locations": []})
    numbers: dict[int, str] = {}
    for entry in entries:
        item = cards[entry["bandai_id"]]
        item["quantity"] += entry["quantity"]
        fake = bool(entry.get("fake"))
        item["fakes"] += entry["quantity"] if fake else 0
        item["locations"].append({
            "id": entry.get("location_id"),
            "name": entry.get("location", ""),
            "kind": entry.get("location_kind", "other"),
            "quantity": entry["quantity"],
            "fake": fake,
            "notes": entry.get("notes", ""),
        })
        numbers[entry["bandai_id"]] = entry["card_number"]
    owned = Owned(dict(cards), numbers)
    cache.set(CACHE_KEY, owned, CACHE_TTL)
    return owned


def _summary(result: dict) -> dict:
    return {"quantity": result["quantity"], "fakes": result.get("fakes", 0), "locations": result["locations"]}


def adjust_owned(card_id: int, delta: int, location: int | None = None, fake: bool | None = None) -> dict:
    """Suma o resta copias de una carta en la colección del escáner.

    Devuelve {quantity, locations} tras el cambio y descarta la colección
    cacheada para que búsqueda y facetas reflejen el cambio al momento. Si hay
    que quitar una copia repartida en varias ubicaciones sin decir cuál, el
    escáner responde 409 con el reparto (CollectionUnavailable.data).
    """
    body = {"bandai_id": card_id, "delta": delta}
    if location:
        body["location"] = location
    if fake is not None:
        body["fake"] = fake
    try:
        result = checker_request("POST", "/api/collection/adjust/", body)
    except CollectionUnavailable as exc:
        if exc.status == 404 and not exc.data.get("detail"):
            exc.args = ("la carta no está en el catálogo del escáner",)
        raise
    cache.delete(CACHE_KEY)
    return _summary(result)


def move_owned(card_id: int, source: int, target: int, quantity: int,
               source_fake: bool = False, target_fake: bool | None = None) -> dict:
    """Mueve copias; con source == target y target_fake distinto, las marca como falsas o auténticas."""
    body = {"bandai_id": card_id, "source": source, "target": target, "quantity": quantity, "source_fake": source_fake}
    if target_fake is not None:
        body["target_fake"] = target_fake
    result = checker_request("POST", "/api/collection/move/", body)
    cache.delete(CACHE_KEY)
    return _summary(result)


def note_owned(card_id: int, location: int, notes: str, fake: bool = False) -> dict:
    result = checker_request("POST", "/api/collection/note/",
                             {"bandai_id": card_id, "location": location, "notes": notes, "fake": fake})
    cache.delete(CACHE_KEY)
    return _summary(result)


KIND_NAMES = {"deck": "mazo", "binder": "archivador", "storage": "almacén", "other": "otro"}


def backup_document(entries: list[dict], exported_at: str, locations: list[dict] | None = None) -> dict:
    """Copia de seguridad de la colección: sus ubicaciones (también las vacías) y
    una fila por carta y ubicación, sin nada que sobre."""
    rows = sorted(entries, key=lambda e: (e["card_number"], e["bandai_id"], e.get("location", ""), bool(e.get("fake"))))
    cards = []
    for e in rows:
        row = {"id": e["bandai_id"], "number": e["card_number"], "name": e["name"],
               "qty": e["quantity"], "location": e.get("location", "")}
        if e.get("fake"):
            row["fake"] = True
        if e.get("notes"):
            row["notes"] = e["notes"]
        cards.append(row)
    places = []
    for loc in locations or []:
        place = {"name": loc["name"], "kind": KIND_NAMES.get(loc.get("kind"), loc.get("kind", "")),
                 "cards": loc.get("cards", 0), "copies": loc.get("copies", 0)}
        if loc.get("fakes"):
            place["fakes"] = loc["fakes"]
        if loc.get("notes"):
            place["notes"] = loc["notes"]
        places.append(place)
    return {
        "format": "dbs-collection",
        "version": 4,
        "exported_at": exported_at,
        "total_cards": len({e["bandai_id"] for e in rows}),
        "total_copies": sum(e["quantity"] for e in rows),
        "total_fakes": sum(e["quantity"] for e in rows if e.get("fake")),
        "locations": places,
        "cards": cards,
    }
