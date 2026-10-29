import logging
import time
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

from vision.preprocess import crop_region, decode_image, encode_jpeg

from . import camera
from .fingerprints import build_pending
from .models import Scan
from .services import apply_burst_rules, run_identification, promote_candidate, resolve_siblings, serialize_candidates, warm_up

logger = logging.getLogger(__name__)


@shared_task
def identify_card(scan_id: int):
    scan = Scan.objects.get(pk=scan_id)
    scan.status = Scan.Status.PROCESSING
    scan.save(update_fields=["status"])
    started = time.monotonic()

    try:
        if scan.image:
            with scan.image.open("rb") as fh:
                data = fh.read()
        else:
            data = camera.get_frame()
            if scan.region:
                # Solo lo que había dentro del marco guía (modo archivador).
                data = encode_jpeg(crop_region(decode_image(data), scan.region))
            scan.image.save(f"scan_{scan.pk}.jpg", ContentFile(data), save=False)

        result = run_identification(decode_image(data))

        scan.cropped_image.save(
            f"scan_{scan.pk}_crop.jpg", ContentFile(encode_jpeg(result.crop)), save=False
        )
        scan.card_detected = result.card_detected
        scan.method = result.method
        scan.candidates = serialize_candidates(result)
        scan.confidence = round(result.confidence, 3) if result.best else None
        scan.matched_card_id = result.best.card_id if result.best else None
        scan.needs_review = result.confidence < settings.MATCH_MIN_CONFIDENCE
        # Impresiones hermanas (promos, Judge…): se decide la edición por sus diferencias; si no
        # se puede, a "Revisar" para que el usuario la elija (en ráfaga no se añade sola).
        doubt, winner = resolve_siblings(scan.candidates, result.crop, scan.pk)
        if doubt and winner:
            scan.candidates = promote_candidate(scan.candidates, winner)
            scan.matched_card_id = winner
        elif doubt:
            scan.needs_review = True
        scan.status = Scan.Status.DONE
    except Exception as exc:  # noqa: BLE001 - el error se guarda en el Scan
        logger.exception("Scan %s falló", scan_id)
        scan.status = Scan.Status.FAILED
        scan.error = str(exc)

    scan.duration_ms = int((time.monotonic() - started) * 1000)
    scan.finished_at = timezone.now()
    scan.save()
    apply_burst_rules(scan)
    return scan.status


@shared_task(ignore_result=True)
def keep_warm():
    """Mantiene en RAM el pipeline de identificación y la cámara (ver warm_up)."""
    warm_up(log=False)
    try:
        camera.get_preview(timeout=3)
    except camera.CameraUnavailable:
        pass  # sin cámara (desarrollo): solo se mantiene caliente el worker


@shared_task
def cleanup_old_scans():
    """Borra las fotos de los escaneos (el registro se conserva): las de más de SCAN_RETENTION_HOURS
    y, si aun así ocupan más de SCAN_PHOTOS_MAX_MB, las más antiguas hasta bajar a SCAN_PHOTOS_TARGET_MB.
    No van en la copia de seguridad: solo sirven para revisar un escaneo reciente."""
    cutoff = timezone.now() - timedelta(hours=settings.SCAN_RETENTION_HOURS)
    removed = 0
    with_photo = Scan.objects.exclude(image="", cropped_image="").order_by("-created_at")
    sizes = [(scan, _photo_bytes(scan)) for scan in with_photo]
    # Lo que ocupan las que no tocan por antigüedad: es lo que cuenta para el límite de tamaño.
    total = sum(size for scan, size in sizes if scan.created_at >= cutoff)
    limit, target = settings.SCAN_PHOTOS_MAX_MB * 2**20, settings.SCAN_PHOTOS_TARGET_MB * 2**20
    kept, full = 0, False
    for scan, size in sizes:  # de la más reciente a la más antigua
        keep = scan.created_at >= cutoff and not full
        if keep and total > limit:
            # Por encima del límite: se conservan las más recientes mientras quepan en el objetivo.
            full = kept + size > target
            keep = not full
        if keep:
            kept += size
            continue
        _delete_photos(scan)
        removed += 1
    return removed


def _photo_bytes(scan) -> int:
    total = 0
    for field in (scan.image, scan.cropped_image):
        if field:
            try:
                total += field.size
            except OSError:  # el fichero ya no está
                pass
    return total


def _delete_photos(scan) -> None:
    for field in (scan.image, scan.cropped_image):
        if field:
            field.delete(save=False)
    scan.save(update_fields=["image", "cropped_image"])


def bootstrap_fingerprints() -> bool:
    """Hay cartas sin huella (instalación nueva con el catálogo de un volcado, o un cálculo que se cortó al
    reiniciar): las calcula en segundo plano. Las cartas que lleguen después las añade el propio sync."""
    from cards.models import Card

    from .models import CardFingerprint

    with_print = CardFingerprint.objects.values("card_id").distinct().count()
    if with_print >= Card.objects.count():
        return False
    build_fingerprints.delay()
    logger.info("Cartas sin huella (%s con huella): se calculan", with_print)
    return True


@shared_task
def build_fingerprints(force: bool = False, card_ids: list[int] | None = None):
    """Huellas de las impresiones nuevas o con imagen cambiada (tras sincronizar o add_printing)."""
    ok, errors = build_pending(force=force, card_ids=card_ids)
    return {"ok": ok, "errors": errors}
