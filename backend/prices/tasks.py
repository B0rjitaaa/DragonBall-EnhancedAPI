"""Tarea diaria: descarga los precios de Cardmarket y rehace los emparejamientos."""
import logging

from celery import shared_task

from . import cardmarket, matching

logger = logging.getLogger(__name__)


@shared_task(name="prices.tasks.sync_prices", autoretry_for=(Exception,), retry_backoff=600, max_retries=3)
def sync_prices() -> dict:
    products, guides = cardmarket.fetch()
    stored = cardmarket.store(products, guides)
    result = {"products": stored, **matching.match_all()}
    logger.info("Precios de Cardmarket: %s", result)
    return result
