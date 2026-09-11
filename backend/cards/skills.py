"""Keyword skills oficiales (https://www.dbs-cardgame.com/us-en/rule/keyword-skills.php).

La web las divide en tres categorías, que usamos tal cual:
- timing  -> "Activate Timing": Permanent, Auto, Activate : Main/Battle…
- skill   -> "Keyword Skills":  Barrier, Blocker, Over Realm X, Counter : Play…
- keyword -> "Keywords":        Limit X, Once per Turn, Bond X, Burst X…

`Catalog` asigna cada habilidad de una carta ('Over Realm 3', 'Once Per Turn') a su nombre
oficial ('Over Realm X', 'Once per Turn'). Lo que no aparece en la web (p. ej. Z-Stack, que es
posterior a su última actualización) se guarda en Keyword Skills con el nombre de su familia.
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

from .parsing import keyword_family, normalize_keyword

logger = logging.getLogger(__name__)

SNAPSHOT_PATH = Path(__file__).parent / "data" / "keyword_skills_snapshot.json"
CATEGORY_FIELDS = {"timing": "timing", "skill": "keyword_skills", "keyword": "keyword_rules"}
SECTIONS = {"Activate-Timing": "timing", "Keyword-Skills": "skill", "Keywords": "keyword"}
PARAM_RE = re.compile(r"^(.*?)\s+(?:X/Y|X|ColorX)$")
MIN_EXPECTED = 40

# Restricciones de construcción de mazo definidas por la propia keyword skill
DECK_RULES = {
    "Ultimate": "Máx. 1 copia en el mazo",
    "Super Combo": "Máx. 4 cartas [Super Combo] en el mazo",
    "Dragon Ball": "Máx. 7 cartas [Dragon Ball] en total",
}


def _key(name: str) -> str:
    return normalize_keyword(name).lower()


class Catalog:
    """Lista oficial de keyword skills + reglas para clasificar las de cada carta."""

    def __init__(self, entries: Iterable[dict]):
        self.entries = sorted(entries, key=lambda e: e.get("order", 0))
        self.by_name = {e["name"]: e for e in self.entries}
        self.exact: dict[str, dict] = {}
        self.prefixes: list[tuple[str, dict]] = []
        for e in self.entries:
            param = PARAM_RE.match(e["name"])
            if param:
                self.prefixes.append((_key(param.group(1)), e))
            else:
                self.exact[_key(e["name"])] = e
        self.prefixes.sort(key=lambda p: -len(p[0]))  # 'dark over realm' antes que 'over realm'

    @classmethod
    def from_snapshot(cls) -> Catalog:
        return cls(json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))["entries"])

    @classmethod
    def from_db(cls) -> Catalog:
        from .models import KeywordSkill

        rows = list(KeywordSkill.objects.values("name", "category", "description", "order"))
        return cls(rows) if rows else cls.from_snapshot()

    def classify(self, keyword: str) -> dict | None:
        k = _key(keyword)
        if k in self.exact:
            return self.exact[k]
        for base, entry in self.prefixes:
            if k == base or k.startswith(base + " "):
                return entry
        return None

    def official_name(self, keyword: str) -> str:
        entry = self.classify(keyword)
        return entry["name"] if entry else keyword_family(normalize_keyword(keyword))

    def assign(self, keywords: Iterable[str]) -> dict[str, list[str]]:
        """{'timing': [...], 'keyword_skills': [...], 'keyword_rules': [...]} con nombres oficiales."""
        out: dict[str, dict[str, None]] = {f: {} for f in CATEGORY_FIELDS.values()}
        for kw in keywords:
            entry = self.classify(kw)
            if entry:
                out[CATEGORY_FIELDS[entry["category"]]][entry["name"]] = None
            else:
                out["keyword_skills"][keyword_family(kw)] = None  # no oficial (Z-Stack…)
        return {f: list(v) for f, v in out.items()}


# --- Web oficial ------------------------------------------------------------------

SECTION_RE = re.compile(r'<section id="([^"]+)"(.*?)</section>', re.S)
BLOCK_RE = re.compile(
    r'<div class="clickBtn[^"]*">\s*<a>(.*?)</a>\s*</div>\s*'
    r'<div class="clickSwitchingCol_inner[^"]*">(.*?)</div>', re.S)
UPDATED_RE = re.compile(r"last updated on ([^)<]+)\)", re.I)
TAG_RE = re.compile(r"<[^>]+>")


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", htmllib.unescape(TAG_RE.sub(" ", fragment))).strip()


def parse_keyword_page(page: str) -> tuple[str, list[dict]]:
    updated = UPDATED_RE.search(page)
    entries, order = [], 0
    for section_id, body in SECTION_RE.findall(page):
        category = SECTIONS.get(section_id)
        if not category:
            continue
        for name, desc in BLOCK_RE.findall(body):
            order += 1
            entries.append({"name": _text(name).strip("[]").strip(), "category": category,
                            "description": _text(desc), "order": order})
    return (updated.group(1).strip() if updated else ""), entries


@transaction.atomic
def store_entries(entries: list[dict], updated: str, source: str) -> None:
    from .models import KeywordSkill

    KeywordSkill.objects.all().delete()
    KeywordSkill.objects.bulk_create([
        KeywordSkill(list_updated=updated, source=source, **e) for e in entries])


def recompute_cards(catalog: Catalog | None = None) -> int:
    """Reasigna timing / keyword_skills / keyword_rules de todas las cartas."""
    from .models import Card

    catalog = catalog or Catalog.from_db()
    batch, total = [], 0
    for card in Card.objects.only("id", "keywords").iterator(chunk_size=1000):
        for field, values in catalog.assign(card.keywords).items():
            setattr(card, field, values)
        batch.append(card)
        if len(batch) >= 1000:
            Card.objects.bulk_update(batch, list(CATEGORY_FIELDS.values()))
            total += len(batch)
            batch.clear()
    if batch:
        Card.objects.bulk_update(batch, list(CATEGORY_FIELDS.values()))
        total += len(batch)
    return total


def sync_keyword_skills() -> dict:
    """Descarga la página oficial; si falla o cambia de formato, se mantiene lo que hay."""
    from curl_cffi import requests as http

    from .importer import invalidate_facets

    resp = http.get(settings.KEYWORD_SKILLS_URL, impersonate="chrome", timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"{resp.status_code} al descargar {settings.KEYWORD_SKILLS_URL}")
    updated, entries = parse_keyword_page(resp.text)
    if len(entries) < MIN_EXPECTED:
        raise RuntimeError(f"Solo {len(entries)} keyword skills: ¿ha cambiado la web oficial?")
    store_entries(entries, updated, "official")
    cards = recompute_cards()
    invalidate_facets()
    return {"updated": updated, "entries": len(entries), "cards": cards}
