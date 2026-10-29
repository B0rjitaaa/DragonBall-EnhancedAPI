"""Descarga de imágenes oficiales y cálculo de fingerprints del catálogo."""

import logging

from django.db.models import Q

from vision import fingerprint as fp
from vision.preprocess import decode_reference, prepare_reference

from cards.models import Card

from .images import get_image
from .models import CardFingerprint

logger = logging.getLogger(__name__)


def _faces(card: Card):
    if card.image_url:
        yield CardFingerprint.Face.FRONT, card.image_url
    if card.back_image_url:
        yield CardFingerprint.Face.BACK, card.back_image_url


def pending_faces(force: bool = False, card_ids=None):
    """(card, face, url) cuyo fingerprint falta o se calculó con otra URL (de esas cartas, si se dicen)."""
    cards = Card.objects.exclude(Q(image_url="") & Q(back_image_url="")).only("id", "card_number", "image_url", "back_image_url")
    if card_ids is not None:
        cards = cards.filter(id__in=card_ids)
    current = {
        (f.card_id, f.face): f.source_url
        for f in CardFingerprint.objects.exclude(face=CardFingerprint.Face.SCAN).only(
            "card_id", "face", "source_url"
        )
    }
    for card in cards.iterator():
        for face, url in _faces(card):
            if force or current.get((card.id, face)) != url:
                yield card, face, url


def build_one(card: Card, face: str, url: str) -> CardFingerprint:
    image = prepare_reference(decode_reference(get_image(url)))
    result = fp.compute(image)
    obj, _ = CardFingerprint.objects.update_or_create(
        card=card,
        face=face,
        defaults={
            "source_url": url,
            "phash": result.phash,
            "dhash": result.dhash,
            "orb": result.orb,
            "orb_count": result.orb_count,
        },
    )
    return obj


def build_pending(force: bool = False, limit: int | None = None, card_ids=None) -> tuple[int, int]:
    """Calcula los fingerprints pendientes (descargando las imágenes que falten). Devuelve (ok, errores)."""
    ok = errors = 0
    for i, (card, face, url) in enumerate(pending_faces(force, card_ids)):
        if limit is not None and i >= limit:
            break
        try:
            build_one(card, face, url)
            ok += 1
        except Exception as exc:  # noqa: BLE001 - una imagen rota no para el lote
            errors += 1
            logger.warning("Fingerprint %s/%s failed: %s", card.card_number, face, exc)
        if (ok + errors) % 500 == 0:
            logger.info("Fingerprints: %s ok, %s errors", ok, errors)
    logger.info("Fingerprints finished: %s ok, %s errors", ok, errors)
    return ok, errors
