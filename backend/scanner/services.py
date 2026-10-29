"""Integración del pipeline de visión con la base de datos."""

import logging
import threading
import time

import numpy as np
from django.conf import settings
from django.db import transaction
from django.db.models import Count, F, Max

from cards.models import Card
from collection.models import CollectionEntry, Location
from vision import fingerprint as fp
from vision.matcher import FingerprintIndex, MatchResult, identify
from vision.preprocess import decode_image, decode_reference, prepare_reference
from vision.siblings import tiebreak

from .images import get_image
from .models import CardFingerprint, Scan

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_cache: dict = {"key": None, "index": None}


def _index_key():
    agg = CardFingerprint.objects.aggregate(n=Count("id"), last=Max("updated_at"))
    return agg["n"], agg["last"]


def get_index() -> FingerprintIndex:
    """Índice de hashes en memoria del worker; se recarga si cambia el catálogo."""
    key = _index_key()
    with _lock:
        if _cache["key"] != key:
            rows = CardFingerprint.objects.values_list("id", "card_id", "phash", "dhash")
            _cache["index"] = FingerprintIndex.from_rows(rows.iterator())
            _cache["key"] = key
        return _cache["index"]


def _load_orb(fingerprint_ids: list[int]) -> dict[int, bytes]:
    return dict(
        CardFingerprint.objects.filter(id__in=fingerprint_ids).values_list("id", "orb")
    )


def run_identification(img) -> MatchResult:
    return identify(
        img,
        get_index(),
        _load_orb,
        hash_threshold=settings.MATCH_HASH_THRESHOLD,
        orb_candidates=settings.MATCH_ORB_CANDIDATES,
    )


def warm_up(log: bool = True):
    """Identificación de prueba (forzando ORB).

    Al arrancar el worker: en la Raspberry Pi la primera identificación tardaba
    ~8 s más que las siguientes, porque OpenCV carga desde la SD el código de
    ORB/BFMatcher la primera vez que se usa.

    Periódicamente (tarea keep_warm): con la RAM justa, Linux manda al swap lo
    que lleva un rato sin usarse y el primer escaneo tras unos minutos parado
    tardaba 3-6 s en recuperarlo.
    """
    started = time.monotonic()
    noise = np.random.default_rng(0).integers(0, 256, (720, 1280, 3), dtype=np.uint8)
    identify(noise, get_index(), _load_orb, hash_threshold=-1, orb_candidates=2)
    if log:
        logger.info("Worker warmed up in %.1f s", time.monotonic() - started)


def learn_from_scan(scan, card) -> CardFingerprint:
    """Guarda el recorte del escaneo como fingerprint de `card` (una por escaneo)."""
    with scan.cropped_image.open("rb") as fh:
        crop = decode_image(fh.read())
    result = fp.compute(crop)
    fingerprint, _ = CardFingerprint.objects.update_or_create(
        scan=scan,
        defaults={
            "card": card,
            "face": CardFingerprint.Face.SCAN,
            "phash": result.phash,
            "dhash": result.dhash,
            "orb": result.orb,
            "orb_count": result.orb_count,
        },
    )
    return fingerprint


def _collection_location(scan) -> Location:
    if scan.session_id and scan.session.location_id:
        return scan.session.location
    return Location.default()


def add_scan_to_collection(scan) -> None:
    """Suma las copias del escaneo (scan.copies) a la colección (idempotente)."""
    if scan.added_to_collection or not scan.matched_card_id:
        return
    copies = max(scan.copies, 1)
    position = scan.binder_position
    with transaction.atomic():
        entry, created = CollectionEntry.objects.select_for_update().get_or_create(
            card_id=scan.matched_card_id,
            location=_collection_location(scan),
            fake=False,
            defaults={"quantity": copies, "notes": position},
        )
        if not created:
            CollectionEntry.objects.filter(pk=entry.pk).update(quantity=F("quantity") + copies)
            if position and position not in entry.notes.splitlines():
                entry.notes = "\n".join(filter(None, [entry.notes, position]))
                entry.save(update_fields=["notes"])
        scan.added_to_collection = True
        scan.collection_entry = entry
        scan.save(update_fields=["added_to_collection", "collection_entry"])


def remove_scan_from_collection(scan) -> None:
    """Deshace add_scan_to_collection: resta sus copias (y borra la entrada si queda a 0)."""
    if not scan.added_to_collection:
        return
    with transaction.atomic():
        entry = (
            CollectionEntry.objects.select_for_update().filter(pk=scan.collection_entry_id).first()
        )
        if entry is not None:
            if entry.quantity <= scan.copies:
                entry.delete()
            else:
                CollectionEntry.objects.filter(pk=entry.pk).update(quantity=F("quantity") - scan.copies)
                position = scan.binder_position
                if position and position in entry.notes.splitlines():
                    entry.notes = "\n".join(line for line in entry.notes.splitlines() if line != position)
                    entry.save(update_fields=["notes"])
        scan.added_to_collection = False
        scan.collection_entry = None
        scan.save(update_fields=["added_to_collection", "collection_entry"])


def set_scan_copies(scan, copies: int) -> None:
    """Cambia cuántas copias suma un escaneo ya añadido (ajusta la colección por la diferencia)."""
    if not scan.added_to_collection:
        scan.copies = copies
        scan.save(update_fields=["copies"])
        return
    with transaction.atomic():
        remove_scan_from_collection(scan)
        scan.copies = copies
        scan.save(update_fields=["copies"])
        add_scan_to_collection(scan)


# Imágenes oficiales ya preparadas (tamaño canónico), por URL: el desempate las reutiliza.
_REFERENCES: dict[str, np.ndarray | None] = {}
_REFERENCES_MAX = 256


def _official_reference(url: str) -> np.ndarray | None:
    if url not in _REFERENCES:
        if len(_REFERENCES) >= _REFERENCES_MAX:
            _REFERENCES.pop(next(iter(_REFERENCES)))
        try:
            _REFERENCES[url] = prepare_reference(decode_reference(get_image(url)))
        except Exception:  # noqa: BLE001 - sin imagen, esa impresión no entra en el desempate
            logger.warning("No reference image for the tie-break: %s", url)
            _REFERENCES[url] = None
    return _REFERENCES[url]


def _learned_reference(card_id: int, exclude_scan: int | None) -> np.ndarray | None:
    """Tu foto confirmada más reciente de esa impresión: compara foto con foto, sin las
    diferencias de color y nitidez de las imágenes oficiales (que vienen de fuentes distintas)."""
    scan = (
        Scan.objects.filter(confirmed=True, dismissed=False, matched_card_id=card_id)
        .exclude(pk=exclude_scan).exclude(cropped_image="").order_by("-id").first()
    )
    if scan is None:
        return None
    try:
        import cv2

        return cv2.imread(scan.cropped_image.path)
    except Exception:  # noqa: BLE001
        return None


def resolve_siblings(candidates: list[dict], crop: np.ndarray, exclude_scan: int | None = None) -> tuple[bool, int | None]:
    """Si los dos mejores candidatos son impresiones hermanas (mismo número), desempata entre
    todas las ediciones de ese número mirando solo donde se diferencian (vision.siblings).

    Devuelve (había_duda, id_ganadora); ganadora None = no se puede decidir: a "Revisar".
    """
    if len(candidates) < 2 or candidates[0]["card_number"] != candidates[1]["card_number"]:
        return False, None
    printings = Card.objects.filter(card_number=candidates[0]["card_number"]).exclude(image_url="").order_by("id")
    ids, references = [], []
    for card in printings.only("id", "image_url"):
        reference = _learned_reference(card.id, exclude_scan)
        if reference is None:
            reference = _official_reference(card.image_url)
        if reference is not None:
            ids.append(card.id)
            references.append(reference)
    if len(references) < 2:
        return True, None
    try:
        result = tiebreak(crop, references)
    except Exception:  # noqa: BLE001 - ante cualquier fallo, mejor preguntar que adivinar
        logger.exception("Tie-break between sibling printings failed")
        return True, None
    return True, (ids[result.winner] if result.winner is not None else None)


def promote_candidate(candidates: list[dict], card_id: int) -> list[dict]:
    """Pone primera la impresión elegida por el desempate (aunque no estuviera en el top)."""
    rest = [c for c in candidates if c["card_id"] != card_id]
    chosen = next((c for c in candidates if c["card_id"] == card_id), None)
    if chosen is None:
        card = Card.objects.get(id=card_id)
        chosen = {**candidates[0], "card_id": card.id, "card_number": card.card_number, "name": card.name,
                  "card_set": card.card_set, "image_url": card.image_url}
    return [chosen, *rest][: max(len(candidates), 1)]


def apply_burst_rules(scan) -> None:
    """Tras identificar un escaneo de una sesión de modo ráfaga."""
    if not scan.session_id or scan.status != scan.Status.DONE:
        return
    confidence = scan.confidence or 0.0
    if not scan.card_detected and confidence < settings.MATCH_MIN_CONFIDENCE:
        # Disparo sobre la zona vacía (se retiró la carta): no es una carta.
        scan.dismissed = True
        scan.save(update_fields=["dismissed"])
    elif _is_repeat(scan):
        # Misma carta que la anterior sin haber vaciado la zona: casi seguro
        # que se ha recolocado. Se pregunta en vez de sumar otra copia.
        scan.repeat_suspect = True
        scan.save(update_fields=["repeat_suspect"])
    elif confidence >= settings.AUTO_ADD_MIN_CONFIDENCE and not scan.needs_review:
        # "Revisar" con confianza alta = no se pudo decidir entre ediciones hermanas: hay que elegirla.
        add_scan_to_collection(scan)


def _is_repeat(scan) -> bool:
    if scan.after_empty or not scan.matched_card_id:
        return False
    previous = (
        scan.session.scans.filter(created_at__lt=scan.created_at, card_detected=True, dismissed=False)
        .exclude(pk=scan.pk)
        .order_by("-created_at")
        .first()
    )
    return previous is not None and previous.matched_card_id == scan.matched_card_id


def serialize_candidates(result: MatchResult, limit: int = 5) -> list[dict]:
    """Candidatos únicos por carta, con los datos necesarios para la UI."""
    seen, unique = set(), []
    for cand in result.candidates:
        if cand.card_id not in seen:
            seen.add(cand.card_id)
            unique.append(cand)
        if len(unique) == limit:
            break

    cards = Card.objects.in_bulk([c.card_id for c in unique])
    output = []
    for cand in unique:
        card = cards.get(cand.card_id)
        if card is None:
            continue
        output.append(
            {
                "card_id": card.id,
                "card_number": card.card_number,
                "name": card.name,
                "card_set": card.card_set,
                "image_url": card.image_url,
                "distance": cand.distance,
                "orb_matches": cand.orb_matches,
                "score": round(
                    max(cand.hash_confidence, cand.orb_confidence)
                    if cand.orb_matches is not None
                    else cand.hash_confidence,
                    3,
                ),
            }
        )
    return output
