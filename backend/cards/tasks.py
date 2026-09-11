"""Tareas en segundo plano (Celery). La programación está en settings.CELERY_BEAT_SCHEDULE."""
from __future__ import annotations

import logging

from celery import shared_task
from django.core.cache import cache
from django.utils import timezone

from . import banlist, skills
from .bandai import BandaiClient
from .importer import upsert_cards
from .models import Card, SyncRun

logger = logging.getLogger(__name__)

LOCK_KEY = "sync-cards-lock"
LOCK_TIMEOUT = 60 * 60 * 3
SAVE_EVERY = 200


@shared_task(name="cards.tasks.sync_cards")
def sync_cards(full: bool = False) -> dict:
    """Sincroniza con Bandai TCG+.

    full=False -> solo descarga las cartas nuevas (ids que no están en la BD).
    full=True  -> vuelve a descargar todas (recoge erratas y cambios de texto).
    """
    if not cache.add(LOCK_KEY, "1", LOCK_TIMEOUT):
        logger.info("Ya hay un sync en marcha; se omite.")
        return {"skipped": True}

    run = SyncRun.objects.create(full=full)
    buffer: list[dict] = []

    def flush() -> None:
        created, updated, errors = upsert_cards(buffer)
        run.created += created
        run.updated += updated
        run.failed_ids += errors
        run.fetched += len(buffer)
        run.save(update_fields=["created", "updated", "failed_ids", "fetched"])
        buffer.clear()

    def on_result(card: dict) -> None:
        buffer.append(card)
        if len(buffer) >= SAVE_EVERY:
            flush()

    try:
        client = BandaiClient()
        ids = client.list_card_ids()
        run.listed = len(ids)
        run.save(update_fields=["listed"])

        if not full:
            existing = set(Card.objects.values_list("id", flat=True))
            ids = [i for i in ids if i not in existing]
        logger.info("Sync: %s cartas listadas, %s a descargar", run.listed, len(ids))

        _, failed = client.fetch_details(ids, on_result=on_result)
        if buffer:
            flush()
        run.failed_ids += failed
        run.status = SyncRun.Status.PARTIAL if run.failed_ids else SyncRun.Status.SUCCESS
    except Exception as exc:  # noqa: BLE001
        if buffer:
            flush()  # no perder lo ya descargado
        logger.exception("Sync fallido")
        run.status = SyncRun.Status.FAILED
        run.error = str(exc)
    finally:
        run.finished_at = timezone.now()
        run.save()
        cache.delete(LOCK_KEY)

    return {
        "run": run.pk, "status": run.status, "listed": run.listed,
        "created": run.created, "updated": run.updated, "failed": len(run.failed_ids),
    }


@shared_task(name="cards.tasks.sync_banlist", autoretry_for=(Exception,), retry_backoff=600, max_retries=3)
def sync_banlist() -> dict:
    """Actualiza la lista oficial de cartas prohibidas/limitadas."""
    return banlist.sync_banlist()


@shared_task(name="cards.tasks.sync_keyword_skills", autoretry_for=(Exception,), retry_backoff=600, max_retries=3)
def sync_keyword_skills() -> dict:
    """Actualiza las keyword skills oficiales (nombres, categorías y textos)."""
    return skills.sync_keyword_skills()
