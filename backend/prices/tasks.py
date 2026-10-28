"""Tarea diaria: descarga los precios de Cardmarket y TCGplayer y recalcula el precio de cada carta."""
import logging

from celery import shared_task

from . import cardmarket, matching, pricing, tcgplayer

logger = logging.getLogger(__name__)


@shared_task(name="prices.tasks.sync_prices", autoretry_for=(Exception,), retry_backoff=600, max_retries=3)
def sync_prices() -> dict:
    """Cardmarket (catálogo y guía del día), TCGplayer (si hay datos nuevos) y el cambio del dólar; luego
    rehace los emparejamientos y el precio de cada carta (y su historial)."""
    products, guides = cardmarket.fetch()
    result = {"products": cardmarket.store(products, guides), **matching.match_all()}
    result["usd_per_eur"] = float(tcgplayer.fetch_rate().usd_per_eur)
    result["tcgplayer"] = tcgplayer.sync()
    result["tcgplayer_links"] = tcgplayer.match_all()
    result["prices"] = pricing.refresh()
    logger.info("Precios: %s", result)
    return result
