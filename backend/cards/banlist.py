"""Lista oficial de cartas prohibidas (Banned) y limitadas (Limited).

Fuente: https://www.dbs-cardgame.com/us-en/rule/banned-limited-cards.php
- `sync_banlist()` descarga y parsea la web oficial (tarea Celery diaria).
- Si la web no responde, se mantiene lo que haya en BD (inicialmente, la copia de
  `data/banlist_snapshot.json` que carga la migración).
- `apply_banlist()` marca `Card.legality` en todas las impresiones con ese card_number.
"""
from __future__ import annotations

import html as htmllib
import json
import logging
import re
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

from django.conf import settings
from django.db import transaction

from .models import BanListEntry, Card, Legality

logger = logging.getLogger(__name__)

SNAPSHOT_PATH = Path(__file__).parent / "data" / "banlist_snapshot.json"
SECTIONS = {"bannedCardList": Legality.BANNED, "limitedCardList": Legality.LIMITED}
MIN_EXPECTED_BANNED = 10  # si el parser encuentra menos, la web ha cambiado: no tocar la BD

UPDATED_RE = re.compile(r"last updated on ([^)<]+)\)", re.I)
BLOCK_RE = re.compile(r'<div class="limitedCardList-inner')
CONTENTS_RE = re.compile(r'<dd class="contents">(.*?)</dd>', re.S)
PERIOD_RE = re.compile(r"<dd>(.*?)</dd>", re.S)
LIMIT_RE = re.compile(r"total (\d+) cop", re.I)
BR_RE = re.compile(r"<br\s*/?>", re.I)
TAG_RE = re.compile(r"<[^>]+>")


class BanListError(RuntimeError):
    pass


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", htmllib.unescape(TAG_RE.sub(" ", fragment))).strip()


def _section(page: str, section_id: str) -> str:
    start = page.find(f'id="{section_id}"')
    if start < 0:
        return ""
    # termina donde empieza la siguiente sección de la página (cualquier otro id de lista)
    ends = [page.find(f'id="{other}', start + 1) for other in ("bannedCardList", "limitedCardList")]
    ends = [e for e in ends if e > start]
    return page[start:min(ends)] if ends else page[start:]


def parse_banlist_html(page: str) -> tuple[str, list[dict]]:
    """Devuelve ('June 19, 2026', [{card_number, status, card_name, limit, since}, ...])."""
    updated = UPDATED_RE.search(page)
    entries: list[dict] = []
    for section_id, status in SECTIONS.items():
        chunk = _section(page, section_id)
        limit_match = LIMIT_RE.search(chunk)
        limit = int(limit_match.group(1)) if (status == Legality.LIMITED and limit_match) else (
            1 if status == Legality.LIMITED else 0)
        for block in BLOCK_RE.split(chunk)[1:]:
            contents = [_text(c) for c in CONTENTS_RE.findall(block)]
            if not contents:
                continue
            periods = PERIOD_RE.findall(block.split("limitedCardCol", 1)[-1])
            since = ""
            if periods:  # "North America, Oceania, Asia<br>From July 3 2026 onward." -> la fecha
                parts = BR_RE.split(periods[0], maxsplit=1)
                since = _text(parts[1] if len(parts) > 1 else parts[0])
            entries.append({
                "card_number": contents[0],
                "status": status,
                "card_name": contents[1] if len(contents) > 1 else "",
                "limit": limit,
                "since": since,
            })
    return (updated.group(1).strip() if updated else ""), entries


def fetch_official() -> str:
    from curl_cffi import requests as http

    resp = http.get(settings.BANLIST_URL, impersonate="chrome", timeout=30)
    if resp.status_code != 200:
        raise BanListError(f"{resp.status_code} al descargar {settings.BANLIST_URL}")
    return resp.text


@transaction.atomic
def store_entries(entries: list[dict], list_updated: str, source: str) -> int:
    BanListEntry.objects.all().delete()
    BanListEntry.objects.bulk_create([
        BanListEntry(list_updated=list_updated, source=source, **e) for e in entries
    ])
    return len(entries)


def load_snapshot() -> int:
    data = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    count = store_entries(data["entries"], data.get("updated", ""), "snapshot")
    apply_banlist()
    return count


def apply_banlist(card_numbers: Iterable[str] | None = None) -> int:
    """Actualiza Card.legality según BanListEntry. Si se pasan card_numbers, solo esos."""
    qs = Card.objects.all()
    entries = BanListEntry.objects.all()
    if card_numbers is not None:
        card_numbers = set(card_numbers)
        qs = qs.filter(card_number__in=card_numbers)
        entries = entries.filter(card_number__in=card_numbers)

    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for e in entries:
        groups[(e.status, e.since)].append(e.card_number)

    with transaction.atomic():
        qs.exclude(legality=Legality.LEGAL).update(legality=Legality.LEGAL, legality_since="")
        changed = 0
        for (status, since), numbers in groups.items():
            changed += qs.filter(card_number__in=numbers).update(legality=status, legality_since=since)
    return changed


def sync_banlist() -> dict:
    """Descarga la lista oficial y la aplica. Si falla, deja la lista actual intacta."""
    page = fetch_official()
    updated, entries = parse_banlist_html(page)
    banned = sum(e["status"] == Legality.BANNED for e in entries)
    if banned < MIN_EXPECTED_BANNED:
        raise BanListError(f"Solo se han encontrado {banned} prohibidas: ¿ha cambiado la web oficial?")
    store_entries(entries, updated, "official")
    cards = apply_banlist()
    from .importer import invalidate_facets

    invalidate_facets()
    result = {"updated": updated, "entries": len(entries), "banned": banned,
              "limited": len(entries) - banned, "cards_marked": cards}
    logger.info("Banlist sincronizada: %s", result)
    return result
