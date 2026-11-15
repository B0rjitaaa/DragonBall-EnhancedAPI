"""Erratas oficiales de las cartas.

Fuente: https://www.dbs-cardgame.com/us-en/rule/errata-cards.php
- `sync_errata()` descarga y parsea la web oficial (tarea Celery semanal).
- Si la web no responde o cambia, se mantiene lo que haya en BD (inicialmente, la copia
  de `data/errata_snapshot.json` que carga la migración).
- `apply_errata()` marca `Card.has_errata` en todas las impresiones con ese card_number. Se vuelve
  a aplicar tras cada sincronización de cartas (el upsert no toca esa marca).
- `find_before()` localiza en el texto de la carta la frase antigua de la errata aunque cambien
  espacios, saltos o comillas; la ficha la cambia por la nueva (el texto guardado es el impreso).
"""
from __future__ import annotations

import html as htmllib
import json
import logging
import re
from collections.abc import Iterable
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
        raise ErrataError(f"{resp.status_code} downloading {settings.ERRATA_URL}")
    return resp.text


@transaction.atomic
def store_entries(entries: list[dict], updated: str, source: str) -> int:
    CardErrata.objects.all().delete()
    CardErrata.objects.bulk_create([
        CardErrata(list_updated=updated, source=source, **e) for e in entries
    ])
    return len(entries)


MIN_PATCH = 20  # textos «antes» más cortos no se buscan (podrían coincidir donde no toca)
_LOOSE = {
    "'": "['’‘]", "’": "['’‘]", "‘": "['’‘]", '"': '["“”]', "“": '["“”]', "”": '["“”]',
    "-": "[-—–]", "—": "[-—–]", "–": "[-—–]", "(": "[(（]", "（": "[(（]", ")": "[)）]", "）": "[)）]",
    "・": "[・•]", "•": "[・•]",
}
_GAP = r"(?:\s|<br\s*/?>)"


def _loose(text: str) -> re.Pattern | None:
    """Patrón que encuentra `text` en el texto de TCG+ aunque cambien espacios, saltos (<br>),
    los espacios alrededor de «:», comillas, guiones o paréntesis de ancho completo."""
    text = re.sub(r"\s*[:：]\s*", ":", BR_RE.sub("\n", text)).strip()
    if len(text) < MIN_PATCH:
        return None
    out = []
    for ch in re.sub(r"\s+", " ", text):
        if ch == " ":
            out.append(f"{_GAP}+")
        elif ch == ":":
            out.append(f"{_GAP}*[:：]{_GAP}*")
        else:
            out.append(_LOOSE.get(ch) or re.escape(ch))
    return re.compile("".join(out))


def find_before(text: str, before: str, after: str = "") -> str | None:
    """Fragmento exacto del texto de la carta que corresponde a la frase antigua de la errata, o
    None si no está o si el texto ya trae la frase nueva (TCG+ a veces ya lo tiene corregido)."""
    old, done = _loose(before), _loose(after)
    found = old.search(text or "") if old else None
    if not found:
        return None
    # Si la errata añade texto, la frase nueva contiene a la antigua: entonces ya está corregido.
    # Si la errata borra texto, la nueva está dentro de la antigua y eso no cuenta.
    if done:
        for m in done.finditer(text):
            if m.start() <= found.start() and found.end() <= m.end():
                return None
    return found.group(0)


def apply_errata(numbers: Iterable[str] | None = None) -> int:
    """Marca Card.has_errata según los números con errata (con `numbers`, solo esas cartas).
    Devuelve cuántas impresiones cambian."""
    errata_numbers = set(CardErrata.objects.values_list("card_number", flat=True))
    cards = Card.objects.all()
    if numbers is not None:
        cards = cards.filter(card_number__in=set(numbers))
    with transaction.atomic():
        changed = cards.filter(has_errata=True).exclude(card_number__in=errata_numbers).update(has_errata=False)
        return changed + cards.filter(card_number__in=errata_numbers, has_errata=False).update(has_errata=True)


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
        raise ErrataError(f"Only {len(entries)} errata found: has the official website changed?")
    old = dict(CardErrata.objects.values_list("card_number", "after"))
    store_entries(entries, updated, "official")
    from .changes import record_errata_changes

    record_errata_changes(old, entries)
    cards = apply_errata()
    from .importer import invalidate_facets

    invalidate_facets()
    result = {"updated": updated, "entries": len(entries), "cards_marked": cards}
    logger.info("Errata synced: %s", result)
    return result
