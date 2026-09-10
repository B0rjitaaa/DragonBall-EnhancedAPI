"""Query builder: convierte un árbol JSON de condiciones AND/OR/NOT en un Q de Django.

Formato:
    grupo     = {"op": "and" | "or", "not": false, "children": [nodo, ...]}
    condición = {"field": "keyword", "operator": "has", "value": "Barrier", "not": false}

Ejemplo — Leaders rojos, O cartas con [Counter: Play] y energía <= 2:
    {"op": "or", "children": [
        {"op": "and", "children": [
            {"field": "type", "operator": "eq", "value": "LEADER"},
            {"field": "color", "operator": "has", "value": "Red"}]},
        {"op": "and", "children": [
            {"field": "keyword", "operator": "has", "value": "Counter: Play"},
            {"field": "energy", "operator": "lte", "value": 2}]}]}
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.db.models import Q

from .parsing import normalize_search

MAX_DEPTH = 6
MAX_CONDITIONS = 60
MAX_VALUES = 100

OPERATORS: dict[str, list[str]] = {
    "text": ["contains", "eq", "startswith"],
    "number": ["eq", "ne", "lt", "lte", "gt", "gte", "between", "isnull"],
    "enum": ["eq", "in"],
    "array": ["has", "has_any", "has_all", "is_empty"],
    "boolean": ["eq"],
}


class QueryError(ValueError):
    pass


@dataclass(frozen=True)
class Field:
    label: str
    type: str
    columns: tuple[str, ...]
    group: str = "Carta"
    facet: bool = field(default=False)  # se ofrecen valores/recuentos en /api/facets/
    normalized: bool = field(default=False)  # columna en formato normalize_search


FIELDS: dict[str, Field] = {
    # Texto
    "name": Field("Nombre", "text", ("name", "back_name"), "Texto"),
    "text": Field("Texto de la carta", "text", ("effect_text",), "Texto", normalized=True),
    "card_number": Field("Número", "text", ("card_number",), "Texto"),
    # Set
    "series": Field("Serie", "enum", ("series",), "Set", facet=True),
    "set_code": Field("Set", "enum", ("set_code",), "Set", facet=True),
    "card_set": Field("Nombre del set", "enum", ("card_set",), "Set", facet=True),
    "regulation": Field("Formato", "array", ("regulations",), "Set", facet=True),
    "legality": Field("Legalidad (Ban/Limit)", "enum", ("legality",), "Torneo", facet=True),
    # card_config
    "type": Field("Tipo", "enum", ("card_type",), "Atributos", facet=True),
    "color": Field("Color", "array", ("colors",), "Atributos", facet=True),
    "rarity": Field("Rareza", "enum", ("rarity",), "Atributos", facet=True),
    "energy": Field("Energía", "number", ("energy",), "Atributos"),
    "color_cost": Field("Coste de color", "array", ("color_cost_colors",), "Atributos", facet=True),
    "combo_energy": Field("Energía de combo", "number", ("combo_energy",), "Atributos"),
    "combo_power": Field("Poder de combo", "number", ("combo_power",), "Atributos"),
    "power": Field("Poder", "number", ("power",), "Atributos"),
    "back_power": Field("Poder (cara trasera)", "number", ("back_power",), "Atributos"),
    "z_energy_cost": Field("Coste Z-Energía", "number", ("z_energy_cost",), "Atributos"),
    "character": Field("Personaje", "array", ("characters",), "Atributos", facet=True),
    "special_trait": Field("Rasgo especial", "array", ("special_traits",), "Atributos", facet=True),
    "era": Field("Era", "array", ("eras",), "Atributos", facet=True),
    "has_back": Field("Tiene cara trasera", "boolean", ("back_id",), "Atributos"),
    # Habilidades
    "keyword": Field("Habilidad", "array", ("keywords",), "Habilidades", facet=True),
    "keyword_family": Field("Familia de habilidad", "array", ("keyword_families",), "Habilidades", facet=True),
}


def fields_schema() -> list[dict[str, Any]]:
    return [
        {"key": key, "label": f.label, "type": f.type, "group": f.group,
         "operators": OPERATORS[f.type], "facet": f.facet}
        for key, f in FIELDS.items()
    ]


# --- Conversión de valores --------------------------------------------------------

def _as_list(value: Any) -> list:
    values = value if isinstance(value, list) else [value]
    values = [v for v in values if v not in (None, "")]
    if not values:
        raise QueryError("Se necesita al menos un valor")
    if len(values) > MAX_VALUES:
        raise QueryError(f"Máximo {MAX_VALUES} valores por condición")
    return values


def _as_number(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        raise QueryError(f"'{value}' no es un número") from None


def _as_text(value: Any) -> str:
    if not isinstance(value, (str, int, float)) or str(value).strip() == "":
        raise QueryError("Se necesita un texto")
    return str(value).strip()[:200]


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if str(value).lower() in {"true", "1", "yes", "si", "sí"}:
        return True
    if str(value).lower() in {"false", "0", "no"}:
        return False
    raise QueryError(f"'{value}' no es un booleano")


# --- Construcción de Q ------------------------------------------------------------

def _any_column(columns: tuple[str, ...], lookup: str, value: Any) -> Q:
    q = Q()
    for col in columns:
        q |= Q(**{f"{col}__{lookup}": value})
    return q


def condition_to_q(node: dict) -> Q:
    key = node.get("field")
    if key not in FIELDS:
        raise QueryError(f"Campo desconocido: {key}")
    f = FIELDS[key]
    op = node.get("operator")
    if op not in OPERATORS[f.type]:
        raise QueryError(f"Operador '{op}' no válido para {key} ({f.type})")
    value = node.get("value")
    col = f.columns[0]

    if f.type == "text":
        text = _as_text(value)
        if f.normalized:
            text = normalize_search(text)
        lookup = {"contains": "icontains", "eq": "iexact", "startswith": "istartswith"}[op]
        q = _any_column(f.columns, lookup, text)

    elif f.type == "number":
        if op == "isnull":
            q = Q(**{f"{col}__isnull": _as_bool(True if value is None else value)})
        elif op == "between":
            if not isinstance(value, (list, tuple)) or len(value) != 2:
                raise QueryError("'between' necesita [mínimo, máximo]")
            lo, hi = value
            q = Q()
            if lo not in (None, ""):
                q &= Q(**{f"{col}__gte": _as_number(lo)})
            if hi not in (None, ""):
                q &= Q(**{f"{col}__lte": _as_number(hi)})
        elif op == "ne":
            q = ~Q(**{col: _as_number(value)}) & Q(**{f"{col}__isnull": False})
        else:
            lookup = {"eq": "exact", "lt": "lt", "lte": "lte", "gt": "gt", "gte": "gte"}[op]
            q = Q(**{f"{col}__{lookup}": _as_number(value)})

    elif f.type == "enum":
        if op == "eq":
            q = Q(**{col: _as_text(value)})
        else:
            q = Q(**{f"{col}__in": [str(v) for v in _as_list(value)]})

    elif f.type == "array":
        if op == "is_empty":
            q = Q(**{col: []})
            if value is not None and not _as_bool(value):
                q = ~q
        elif op == "has":
            q = Q(**{f"{col}__contains": [_as_text(value)]})
        elif op == "has_any":
            q = Q(**{f"{col}__overlap": [str(v) for v in _as_list(value)]})
        else:  # has_all
            q = Q(**{f"{col}__contains": [str(v) for v in _as_list(value)]})

    else:  # boolean (has_back)
        q = Q(**{f"{col}__isnull": not _as_bool(value)})

    return ~q if node.get("not") else q


def tree_to_q(node: dict | None) -> Q:
    """Valida y convierte el árbol completo. Lanza QueryError si algo no es válido."""
    if not node:
        return Q()
    counter = {"conditions": 0}
    return _node_to_q(node, depth=1, counter=counter)


def _node_to_q(node: Any, depth: int, counter: dict) -> Q:
    if not isinstance(node, dict):
        raise QueryError("Cada nodo debe ser un objeto")
    if depth > MAX_DEPTH:
        raise QueryError(f"Máximo {MAX_DEPTH} niveles de anidación")

    if "field" in node:
        counter["conditions"] += 1
        if counter["conditions"] > MAX_CONDITIONS:
            raise QueryError(f"Máximo {MAX_CONDITIONS} condiciones")
        return condition_to_q(node)

    op = node.get("op", "and")
    if op not in {"and", "or"}:
        raise QueryError(f"Operador de grupo no válido: {op}")
    children = node.get("children") or []
    if not isinstance(children, list):
        raise QueryError("'children' debe ser una lista")

    q = Q()
    for child in children:
        child_q = _node_to_q(child, depth + 1, counter)
        q = (q & child_q) if op == "and" else (q | child_q)
    return ~q if node.get("not") and children else q


def params_to_tree(params) -> dict:
    """Filtros sencillos por querystring (GET /api/cards/?color=Red&energy_max=3&keyword=Barrier).

    - enum/array con varios valores: OR dentro del campo (usa <campo>_match=all para AND en arrays)
    - número: <campo>=N, <campo>_min, <campo>_max
    - texto: <campo>=texto (contiene)
    """
    children: list[dict] = []
    for key, f in FIELDS.items():
        if f.type == "number":
            if params.get(key) not in (None, ""):
                children.append({"field": key, "operator": "eq", "value": params.get(key)})
            lo, hi = params.get(f"{key}_min"), params.get(f"{key}_max")
            if lo not in (None, "") or hi not in (None, ""):
                children.append({"field": key, "operator": "between", "value": [lo, hi]})
            continue
        values = [v for v in params.getlist(key) if v != ""] if hasattr(params, "getlist") else (
            [params[key]] if params.get(key) else [])
        if not values:
            continue
        if f.type == "text":
            children.append({"field": key, "operator": "contains", "value": values[0]})
        elif f.type == "enum":
            children.append({"field": key, "operator": "in", "value": values})
        elif f.type == "array":
            op = "has_all" if params.get(f"{key}_match") == "all" else "has_any"
            children.append({"field": key, "operator": op, "value": values})
        elif f.type == "boolean":
            children.append({"field": key, "operator": "eq", "value": values[0]})
    return {"op": "and", "children": children}
