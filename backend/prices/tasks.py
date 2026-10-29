"""Tarea diaria: descarga los precios de Cardmarket y TCGplayer y recalcula el precio de cada carta."""
import logging

from celery import shared_task
from django.conf import settings
from django.core.cache import cache

from . import cardmarket, matching, pricing, snapshot, tcgplayer

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
    snapshot.refresh_file(settings.PRICES_SNAPSHOT)
    logger.info("Prices: %s", result)
    return result


def bootstrap_prices() -> bool:
    """Instalación nueva: hay cartas pero ningún precio (el catálogo llegó después de arrancar, o no había
    volcado). Carga el volcado si lo hay (con las elecciones a mano de la revisión) y, si no, encola la
    descarga ya, sin esperar a las 05:15. Una sola vez aunque se llame desde varios sitios."""
    from cards.models import Card

    from .models import CardPrice

    if CardPrice.objects.exists() or not Card.objects.exists():
        return False
    if not cache.add("prices-bootstrap", 1, 3 * 3600):
        return False
    source = snapshot.source_file()
    if source:
        try:
            logger.info("No prices: loading them from the dump %s: %s", source, snapshot.load(source))
            return True
        except (OSError, ValueError):
            logger.warning("Unreadable price dump: downloading them", exc_info=True)
    sync_prices.delay()
    logger.info("No prices: starting the first download")
    return True
