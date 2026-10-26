"""Preguntas y respuestas oficiales por carta (Card Q&A).

Fuente: https://www.dbs-cardgame.com/us-en/rule/card_faq.php
- `sync_rulings()` descarga y parsea la web oficial (tarea Celery semanal).
- Si la web no responde o cambia, se mantiene lo que haya en BD (inicialmente, la copia
  de `data/rulings_snapshot.json` que carga la migración).
- `apply_rulings()` actualiza `Card.rulings_count` en todas las impresiones con ese card_number.
"""
from __future__ import annotations

import html as htmllib
import json
import logging
import re
from collections import Counter
from pathlib import Path

from django.conf import settings
from django.db import transaction

from .models import Card, CardRuling

logger = logging.getLogger(__name__)

SNAPSHOT_PATH = Path(__file__).parent / "data" / "rulings_snapshot.json"
MIN_EXPECTED = 500  # si el parser encuentra menos, la web ha cambiado: no tocar la BD

NUM_RE = re.compile(r"^[A-Z]{1,4}\d{0,2}-\d{1,4}$")
TAG_RE = re.compile(r"<[^>]+>")
BR_RE = re.compile(r"<br\s*/?>", re.I)


class RulingsError(RuntimeError):
    pass


def _text(fragment: str) -> str:
    s = BR_RE.sub("\n", fragment or "")
    s = htmllib.unescape(TAG_RE.sub("", s)).replace("　", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return "\n".join(line.strip() for line in s.splitlines()).strip()


def parse_faq_html(page: str) -> tuple[str, list[dict]]:
    """Devuelve ('', [{card_number, card_name, order, question, answer, is_new, set_label}, ...])."""
    sets = [(m.start(), _text(m.group(1)))
            for m in re.finditer(r'<h4[^>]*class="[^"]*subTitle[^"]*"[^>]*>(.*?)</h4>', page, re.S)]

    def set_for(pos: int) -> str:
        label = ""
        for start, lbl in sets:
            if start <= pos:
                label = lbl
            else:
                break
        return label

    entries: list[dict] = []
    orders: Counter = Counter()  # una misma carta puede salir en varias secciones: numera correlativo
    cards = list(re.finditer(r'<h5 class="points[^"]*">(.*?)</h5>', page, re.S))
    for i, match in enumerate(cards):
        header = _text(match.group(1)).split(None, 1)
        if not header or not NUM_RE.match(header[0].upper()):
            continue
        card_number = header[0].upper()
        card_name = header[1] if len(header) > 1 else ""
        set_label = set_for(match.start())
        end = cards[i + 1].start() if i + 1 < len(cards) else len(page)
        for dl in re.finditer(r'<dl class="faqCol">(.*?)</dl>', page[match.end():end], re.S):
            body = dl.group(1)
            question = re.search(r"<dt>(.*?)</dt>", body, re.S)
            answer = re.search(r"<dd>(.*?)</dd>", body, re.S)
            if question is None or answer is None:
                continue
            orders[card_number] += 1
            entries.append({
                "card_number": card_number,
                "card_name": card_name,
                "order": orders[card_number],
                "question": _text(re.sub(r"<i>.*?</i>", "", question.group(1), count=1, flags=re.S)),
                "answer": _text(re.sub(r"<i>.*?</i>", "", answer.group(1), count=1, flags=re.S)),
                "is_new": ("qaNewQIcon" in body or "qanewIcon" in body),
                "set_label": set_label,
            })
    return "", entries


def fetch_official() -> str:
    from curl_cffi import requests as http

    resp = http.get(settings.CARD_FAQ_URL, impersonate="chrome", timeout=30)
    if resp.status_code != 200:
        raise RulingsError(f"{resp.status_code} al descargar {settings.CARD_FAQ_URL}")
    return resp.text


@transaction.atomic
def store_entries(entries: list[dict], updated: str, source: str) -> int:
    CardRuling.objects.all().delete()
    CardRuling.objects.bulk_create([
        CardRuling(list_updated=updated, source=source, **e) for e in entries
    ])
    return len(entries)


def apply_rulings() -> int:
    """Actualiza Card.rulings_count con el número de Q&A de cada card_number."""
    counts = Counter(CardRuling.objects.values_list("card_number", flat=True))
    with transaction.atomic():
        Card.objects.exclude(rulings_count=0).exclude(card_number__in=counts).update(rulings_count=0)
        changed = 0
        # agrupar por recuento para hacer pocos UPDATE
        by_count: dict[int, list[str]] = {}
        for number, n in counts.items():
            by_count.setdefault(n, []).append(number)
        for n, numbers in by_count.items():
            changed += Card.objects.filter(card_number__in=numbers).exclude(rulings_count=n).update(rulings_count=n)
    return changed


def load_snapshot() -> int:
    data = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    count = store_entries(data["entries"], data.get("updated", ""), "snapshot")
    apply_rulings()
    return count


def sync_rulings() -> dict:
    """Descarga el Card Q&A oficial y lo aplica. Si falla, deja lo que haya intacto."""
    page = fetch_official()
    updated, entries = parse_faq_html(page)
    if len(entries) < MIN_EXPECTED:
        raise RulingsError(f"Solo se han encontrado {len(entries)} Q&A: ¿ha cambiado la web oficial?")
    old = set(CardRuling.objects.values_list("card_number", "question"))
    store_entries(entries, updated, "official")
    from .changes import record_ruling_changes

    record_ruling_changes(old, entries)
    cards = apply_rulings()
    from .importer import invalidate_facets

    invalidate_facets()
    result = {"entries": len(entries), "cards_with_qa": len(set(e["card_number"] for e in entries)),
              "cards_marked": cards}
    logger.info("Card Q&A sincronizado: %s", result)
    return result
