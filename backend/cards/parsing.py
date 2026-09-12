"""Convierte el JSON de Bandai TCG+ en campos normalizados y buscables."""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from typing import Any

BRACKET_RE = re.compile(r"\[([^\[\]]{1,60})\]")
NUMERIC_TOKEN_RE = re.compile(r"^[+\-]?(\d+|X)$")
COLOR = r"(?:Red|Blue|Green|Yellow|Black|White)"
# Sufijo de parámetros: 'Limit 1', 'Revive Blue/Green', 'Empower Red 3/Yellow 3', 'Spirit Boost X'
FAMILY_SUFFIX_RE = re.compile(rf"(?:\s+(?:{COLOR}(?:\s*\d+)?|\d+|X)(?:/(?:{COLOR}(?:\s*\d+)?|\d+))*)+$")
JP_COLORS = {"赤": "Red", "青": "Blue", "緑": "Green", "黄": "Yellow", "黒": "Black", "白": "White"}
KEYWORD_ALIASES = {"Doube Strike": "Double Strike", "Energy Exhaust": "Energy-Exhaust", "Union Potara": "Union-Potara"}
# 'Activate Main' (sin dos puntos) -> 'Activate: Main'
MISSING_COLON_RE = re.compile(r"^(Activate|Counter) (?=[A-Z])")
LOWER_WORD_RE = re.compile(r"(?<![A-Za-z])([a-z])([a-z]*)")
CARD_NUMBER_RE = re.compile(r"^([A-Z]+)(\d+)?-(\d+)")
RARITY_RE = re.compile(r"^(.*?)\s*\[([^\]]+)\]\s*$")
COLOR_COST_RE = re.compile(r"\(([^)]+)\)")
INT_RE = re.compile(r"-?\d+")
BR_RE = re.compile(r"<br\s*/?>", re.I)
TAG_RE = re.compile(r"<[^>]+>")


def normalize_search(value: str | None) -> str:
    """Texto plano para búsquedas: sin corchetes ni HTML, espacios unificados y en minúsculas.

    '[Auto] ... it gains [Barrier]<br>[Activate : Main]' -> 'auto ... it gains barrier activate: main'
    Así 'it gains Barrier' encuentra 'it gains [Barrier]'.
    """
    s = unicodedata.normalize("NFKC", value or "")
    s = TAG_RE.sub(" ", BR_RE.sub(" ", s))
    s = s.replace("[", " ").replace("]", " ").replace("{", " ").replace("}", " ")
    s = re.sub(r"\s*:\s*", ": ", s)
    s = re.sub(r"\s+", " ", s)
    # los corchetes dejan espacios sueltos antes de la puntuación: 'barrier ,' -> 'barrier,'
    s = re.sub(r"\s+([,.;)])", r"\1", s).replace("( ", "(")
    return s.strip().lower()


def clean(value: Any) -> str | None:
    """'' y None -> None; strings recortados."""
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def to_int(value: Any) -> int | None:
    value = clean(value)
    if value is None:
        return None
    match = INT_RE.search(value.replace(",", ""))
    return int(match.group()) if match else None


def normalize_attr(value: str) -> str:
    """Unifica variantes de Bandai: 'Dr.Myuu' -> 'Dr. Myuu', 'Universe7' -> 'Universe 7',
    'DBS：SUPER HERO Saga' -> 'DBS : SUPER HERO Saga'."""
    s = unicodedata.normalize("NFKC", value)
    s = re.sub(r"\.(?=[A-Z])", ". ", s)
    s = re.sub(r"(?<=[a-z])(?=\d)", " ", s)
    s = re.sub(r"\s*:\s*", " : ", s)
    return re.sub(r"\s+", " ", s).strip()


def split_multi(value: Any) -> list[str]:
    """'Saiyan/Earthling' -> ['Saiyan', 'Earthling'] (sin duplicados, en orden)."""
    value = clean(value)
    if not value:
        return []
    parts = [normalize_attr(p) for p in value.split("/")]
    return list(dict.fromkeys(p for p in parts if p))


def config_to_dict(config: list[dict] | None) -> dict[str, str | None]:
    return {item.get("config_name"): clean(item.get("value")) for item in (config or []) if item.get("config_name")}


# --- Keywords -----------------------------------------------------------------

def normalize_keyword(raw: str) -> str:
    """Unifica variantes: 'Activate : Main' / 'Activate: Main', 'Once per turn' / 'Once Per Turn'."""
    s = unicodedata.normalize("NFKC", raw)  # '：' -> ':', '２' -> '2'
    for jp, en in JP_COLORS.items():
        s = s.replace(jp, en)
    s = re.sub(r"\((\w+)\)", r"\1", s)  # 'Empower (Red)3' -> 'Empower Red3'
    s = re.sub(r"(?<=[a-z])(?=\d)", " ", s)  # 'Empower Red3' -> 'Empower Red 3'
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s*:\s*", ": ", s)
    s = re.sub(r"\s*/\s*", "/", s)
    s = LOWER_WORD_RE.sub(lambda m: m.group(1).upper() + m.group(2), s)
    s = MISSING_COLON_RE.sub(r"\1: ", s)
    return KEYWORD_ALIASES.get(s, s)


def keyword_family(kw: str) -> str:
    """'Counter: Play' -> 'Counter', 'Limit 1' -> 'Limit', 'Arrival Red/Green' -> 'Arrival'."""
    if ": " in kw:
        return kw.split(": ", 1)[0]
    return FAMILY_SUFFIX_RE.sub("", kw) or kw


def _is_own_skill(text: str, start: int) -> bool:
    """¿El corchete que empieza en `start` es una habilidad de la carta o solo una mención?

    Las habilidades propias van al inicio de línea o encadenadas: '[Auto][Once per turn] …',
    '…<br>[Barrier]'. Las menciones van dentro de una frase: 'it gains [Barrier]',
    'activates [Revive]', 'isn't affected by [Counter : Play] skills'.
    """
    line = text[:start].rsplit("\n", 1)[-1]
    if line.count("(") > line.count(")"):
        return False  # texto recordatorio entre paréntesis: '(… [Over Realm] can only be …)'
    before = line.rstrip(" \t")
    return not before or before[-1] in "]).:"


def _expand(kw: str) -> list[str]:
    # 'Activate: Main/Battle' también cuenta como 'Activate: Main' y 'Activate: Battle'
    out = [kw]
    if ": " in kw:
        prefix, rest = kw.split(": ", 1)
        if "/" in rest:
            out += [f"{prefix}: {part}" for part in rest.split("/")]
    return out


def extract_keywords(*texts: str | None, own: Iterable[str] = ()) -> tuple[list[str], list[str], list[str]]:
    """Devuelve (habilidades propias, familias, menciones) a partir de los corchetes del texto.

    `own` son valores que siempre cuentan como propios (p. ej. el campo 'Keyword Skill').
    """
    keywords: dict[str, None] = {}
    mentions: dict[str, None] = {}
    for value in own:
        for raw in BRACKET_RE.findall(value or "") or [value or ""]:
            kw = normalize_keyword(raw)
            if kw and not NUMERIC_TOKEN_RE.match(kw):
                keywords.update(dict.fromkeys(_expand(kw)))
    for text in texts:
        plain = BR_RE.sub("\n", text or "")
        for match in BRACKET_RE.finditer(plain):
            kw = normalize_keyword(match.group(1))
            if not kw or NUMERIC_TOKEN_RE.match(kw):
                continue  # [+1], [-3]… son marcadores de coste, no habilidades
            target = keywords if _is_own_skill(plain, match.start()) else mentions
            target.update(dict.fromkeys(_expand(kw)))

    families = dict.fromkeys(keyword_family(kw) for kw in keywords)
    return list(keywords), list(families), [m for m in mentions if m not in keywords]


# --- Card ---------------------------------------------------------------------

def parse_card_number(card_number: str) -> dict[str, Any]:
    match = CARD_NUMBER_RE.match(card_number or "")
    if not match:
        return {"series": "", "set_number": None, "collector_number": None, "set_code": ""}
    series, set_number, collector = match.groups()
    return {
        "series": series,
        "set_number": int(set_number) if set_number else None,
        "collector_number": int(collector),
        "set_code": f"{series}{set_number or ''}",
    }


def parse_rarity(value: str | None) -> tuple[str, str]:
    value = clean(value)
    if not value:
        return "", ""
    match = RARITY_RE.match(value)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return value, value


def parse_card(data: dict) -> dict[str, Any]:
    """Recibe el detalle de /api/user/card/{id} y devuelve los campos del modelo Card."""
    cfg = config_to_dict(data.get("card_config"))
    back_cfg = config_to_dict(data.get("backcard_card_config"))
    rarity, rarity_code = parse_rarity(cfg.get("Rarity"))
    card_number = clean(data.get("card_number")) or ""

    # Bandai a veces apunta 'backcard_*' a OTRA carta (BT4-107 -> Zamasu BT26-061).
    # Solo es cara trasera de verdad si comparte número de carta.
    has_back = bool(data.get("backcard_id")) and (clean(data.get("backcard_card_number")) or card_number) == card_number
    if not has_back:
        back_cfg = {}
    back = {
        "id": data.get("backcard_id") or None,
        "card_name": clean(data.get("backcard_card_name")) or "",
        "card_text": clean(data.get("backcard_card_text")) or "",
        "image_url": clean(data.get("backcard_image_url")) or "",
    } if has_back else {}

    keywords, families, mentions = extract_keywords(
        data.get("card_text"),
        data.get("card_text2"),
        data.get("backcard_card_text") if has_back else None,
        own=[cfg.get("Keyword Skill") or "", back_cfg.get("Keyword Skill") or ""],
    )

    return {
        "id": int(data["id"]),
        "card_number": card_number,
        "name": clean(data.get("card_name")) or "",
        "text": clean(data.get("card_text")) or "",
        "image_url": clean(data.get("image_url")) or "",
        "card_set": clean(data.get("card_set")) or "",
        **parse_card_number(card_number),
        "card_type": (cfg.get("Type") or "").upper(),  # a veces viene 'Battle' en vez de 'BATTLE'
        "colors": split_multi(cfg.get("Color")),
        "rarity": rarity,
        "rarity_code": rarity_code,
        "energy": to_int(cfg.get("Energy")),
        "color_cost": cfg.get("Color Cost") or "",
        "color_cost_colors": COLOR_COST_RE.findall(cfg.get("Color Cost") or ""),
        "combo_energy": to_int(cfg.get("Combo Energy")),
        "combo_power": to_int(cfg.get("Combo power") or cfg.get("Combo Power")),
        "power": to_int(cfg.get("Power")),
        "z_energy_cost": to_int(cfg.get("Z-Energy Cost")),
        "characters": split_multi(cfg.get("Character")),
        "special_traits": split_multi(cfg.get("Special Trait")),
        "eras": split_multi(cfg.get("Era")),
        "notes": cfg.get("Notes") or "",
        "keywords": keywords,
        "keyword_families": families,
        "keyword_mentions": mentions,
        "regulations": [r["title"] for r in (data.get("regulations") or []) if r.get("title")],
        "back_id": back.get("id"),
        "back_name": back.get("card_name") or "",
        "back_text": back.get("card_text") or "",
        "back_image_url": back.get("image_url") or "",
        "back_power": to_int(back_cfg.get("Power")),
        "effect_text": normalize_search(f"{data.get('card_text') or ''} {back.get('card_text') or ''}"),
        "search_text": normalize_search(" ".join(str(x) for x in (
            data.get("card_name"), back.get("card_name"), card_number,
            data.get("card_text"), back.get("card_text"),
        ) if x)),
        "config": cfg,
        "back_config": back_cfg,
        "raw": data,
    }
