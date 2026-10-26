"""Erratas oficiales de las cartas.

Fuente: https://www.dbs-cardgame.com/us-en/rule/errata-cards.php
- `sync_errata()` descarga y parsea la web oficial (tarea Celery semanal).
- Si la web no responde o cambia, se mantiene lo que haya en BD (inicialmente, la copia
  de `data/errata_snapshot.json` que carga la migración).
- `apply_errata()` marca `Card.has_errata` en todas las impresiones con ese card_number.
"""
from __future__ import annotations

import html as htmllib
import json
import logging
import re
from pathlib import Path

from django.conf import settings
from django.db import transaction

from .models import Card, CardErrata

logger = logging.getLogger(__name__)

SNAPSHOT_PATH = Path(__file__).parent / "data" / "errata_snapshot.json"
MIN_EXPECTED = 50  # si el parser encuentra menos, la web ha cambiado: no tocar la BD

UPDATED_RE = re.compile(r"updated on ([^)<]+)\)", re.I)
TAG_RE = re.compile(r"<[^>]+>")
BR_RE = re.compile(r"<br\s*/?>", re.I)


class ErrataError(RuntimeError):
    pass


def _text(fragment: str) -> str:
    s = BR_RE.sub("\n", fragment or "")
    s = htmllib.unescape(TAG_RE.sub("", s)).replace("　", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return "\n".join(line.strip() for line in s.splitlines()).strip()


def _abs_url(src: str) -> str:
    src = (src or "").strip()
    if not src or src.startswith("http"):
        return src
    return "https://www.dbs-cardgame.com" + src.replace("../../", "/").lstrip(".")


def parse_errata_html(page: str) -> tuple[str, list[dict]]:
    """Devuelve ('August 22, 2025', [{card_number, card_name, before, after, notes, image_url, date}, ...])."""
    updated = UPDATED_RE.search(page)
    entries: list[dict] = []
    for chunk in re.split(r'<dt class="title">', page)[1:]:
        title = _text(chunk.split("</dt>", 1)[0])
        num = re.search(r"Card No:\s*([A-Za-z0-9-]+)", chunk)
        if num is None:
            num = re.search(r"\b([A-Z]{1,4}\d{0,2}-\d{1,4})\b", title)
        if num is None:
            continue
        name = re.search(r"Card Name:\s*(.*?)</p>", chunk, re.S)
        img = re.search(r'<img[^>]+src="([^"]+errata-cards/[^"]+)"', chunk)
        before = re.search(r"beforeCol.*?<p[^>]*>(.*?)</p>", chunk, re.S)
        after = re.search(r"afterCol.*?<p[^>]*>(.*?)</p>", chunk, re.S)
        notes = re.search(r"errataNotes.*?<dd>(.*?)</dd>", chunk, re.S)
        date = re.match(r"([\d.]{8,10})", title)
        entries.append({
            "card_number": num.group(1).strip().upper(),
            "card_name": _text(name.group(1)) if name else "",
            "before": _text(before.group(1)) if before else "",
            "after": _text(after.group(1)) if after else "",
            "notes": _text(notes.group(1)) if notes else "",
            "image_url": _abs_url(img.group(1)) if img else "",
            "date": date.group(1) if date else "",
        })
    return (updated.group(1).strip() if updated else ""), entries


def fetch_official() -> str:
    from curl_cffi import requests as http

    resp = http.get(settings.ERRATA_URL, impersonate="chrome", timeout=30)
    if resp.status_code != 200:
        raise ErrataError(f"{resp.status_code} al descargar {settings.ERRATA_URL}")
    return resp.text


@transaction.atomic
def store_entries(entries: list[dict], updated: str, source: str) -> int:
    CardErrata.objects.all().delete()
    CardErrata.objects.bulk_create([
        CardErrata(list_updated=updated, source=source, **e) for e in entries
    ])
    return len(entries)


def apply_errata() -> int:
    """Marca Card.has_errata según los números con errata."""
    numbers = set(CardErrata.objects.values_list("card_number", flat=True))
    with transaction.atomic():
        Card.objects.filter(has_errata=True).exclude(card_number__in=numbers).update(has_errata=False)
        return Card.objects.filter(card_number__in=numbers, has_errata=False).update(has_errata=True)


def load_snapshot() -> int:
    data = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    count = store_entries(data["entries"], data.get("updated", ""), "snapshot")
    apply_errata()
    return count


def sync_errata() -> dict:
    """Descarga las erratas oficiales y las aplica. Si falla, deja lo que haya intacto."""
    page = fetch_official()
    updated, entries = parse_errata_html(page)
    if len(entries) < MIN_EXPECTED:
        raise ErrataError(f"Solo se han encontrado {len(entries)} erratas: ¿ha cambiado la web oficial?")
    store_entries(entries, updated, "official")
    cards = apply_errata()
    from .importer import invalidate_facets

    invalidate_facets()
    result = {"updated": updated, "entries": len(entries), "cards_marked": cards}
    logger.info("Erratas sincronizadas: %s", result)
    return result
