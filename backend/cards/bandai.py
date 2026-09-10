"""Cliente de la API pública de Bandai TCG+ con control de ritmo y reintentos ante bloqueos."""
from __future__ import annotations

import logging
import random
import threading
import time
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed

from curl_cffi import requests as http
from django.conf import settings

logger = logging.getLogger(__name__)

PAGE_LIMIT = 500
TIMEOUT = 20
MAX_ATTEMPTS = 8
BLOCK_STATUS = {403, 429}
RETRY_STATUS = {500, 502, 503, 504}

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Origin": "https://www.bandai-tcg-plus.com",
    "Referer": "https://www.bandai-tcg-plus.com/",
}


class BandaiError(RuntimeError):
    pass


class Throttle:
    """Ritmo global entre hilos + pausa compartida cuando la API bloquea (403/429)."""

    def __init__(self, delay: float, base_cooldown: float = 60.0, max_cooldown: float = 900.0):
        self.delay = delay
        self.base_cooldown = base_cooldown
        self.max_cooldown = max_cooldown
        self.cooldown = base_cooldown
        self.lock = threading.Lock()
        self.next_slot = 0.0
        self.paused_until = 0.0

    def wait(self) -> None:
        with self.lock:
            now = time.monotonic()
            slot = max(now, self.next_slot, self.paused_until)
            self.next_slot = slot + self.delay
        time.sleep(max(0.0, slot - time.monotonic()))

    def blocked(self, status: int) -> None:
        with self.lock:
            now = time.monotonic()
            if now < self.paused_until:
                return
            wait = self.cooldown
            self.paused_until = now + wait
            self.cooldown = min(self.cooldown * 2, self.max_cooldown)
        logger.warning("Bandai devolvió %s: pausa de %.0fs", status, wait)

    def ok(self) -> None:
        self.cooldown = self.base_cooldown


class BandaiClient:
    def __init__(self, base_url: str | None = None, game_id: int | None = None,
                 delay: float | None = None, workers: int | None = None):
        self.base_url = (base_url or settings.BANDAI_API_URL).rstrip("/")
        self.game_id = game_id or settings.BANDAI_GAME_TITLE_ID
        self.workers = workers or settings.BANDAI_WORKERS
        self.throttle = Throttle(settings.BANDAI_REQUEST_DELAY if delay is None else delay)
        self._local = threading.local()

    def _session(self):
        if not hasattr(self._local, "session"):
            session = http.Session(impersonate="chrome")
            session.headers.update(BROWSER_HEADERS)
            self._local.session = session
        return self._local.session

    def get(self, path: str, **params) -> dict:
        url = f"{self.base_url}{path}"
        for attempt in range(1, MAX_ATTEMPTS + 1):
            self.throttle.wait()
            try:
                resp = self._session().get(url, params=params, timeout=TIMEOUT)
            except Exception as exc:  # noqa: BLE001
                if attempt == MAX_ATTEMPTS:
                    raise BandaiError(f"Error de red en {url}: {exc}") from exc
                time.sleep(2 ** attempt)
                continue
            if resp.status_code in BLOCK_STATUS:
                self.throttle.blocked(resp.status_code)
                continue
            if resp.status_code in RETRY_STATUS:
                time.sleep(2 ** attempt + random.random())
                continue
            if resp.status_code >= 400:
                raise BandaiError(f"{resp.status_code} en {url}")
            self.throttle.ok()
            payload = resp.json()
            if "success" not in payload:
                raise BandaiError(f"Respuesta inesperada en {url}: {str(payload)[:200]}")
            return payload["success"]
        raise BandaiError(f"Sin respuesta válida tras {MAX_ATTEMPTS} intentos: {url}")

    def list_card_ids(self) -> list[int]:
        ids: dict[int, None] = {}
        offset = 0
        while True:
            data = self.get("/card/list", game_title_id=self.game_id, limit=PAGE_LIMIT, offset=offset)
            page = data.get("cards") or []
            if not page:
                break
            before = len(ids)
            for card in page:
                ids[int(card["id"])] = None
            if len(ids) == before:
                break
            offset += len(page)
        return list(ids)

    def card_detail(self, card_id: int) -> dict:
        return self.get(f"/card/{card_id}")["card"]

    def fetch_details(self, ids: Iterable[int],
                      on_result: Callable[[dict], None] | None = None) -> tuple[list[dict], list[int]]:
        """Descarga el detalle de varias cartas en paralelo. Devuelve (cartas, ids_fallidos)."""
        results: list[dict] = []
        failed: list[int] = []
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            futures = {pool.submit(self.card_detail, cid): cid for cid in ids}
            for fut in as_completed(futures):
                cid = futures[fut]
                try:
                    card = fut.result()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Carta %s: %s", cid, exc)
                    failed.append(cid)
                    continue
                results.append(card)
                if on_result:
                    on_result(card)
        return results, failed
