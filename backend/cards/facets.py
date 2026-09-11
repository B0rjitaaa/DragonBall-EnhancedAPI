"""Valores disponibles y recuentos por atributo, para el panel de filtros facetados."""
from __future__ import annotations

import hashlib
import json

from django.core.cache import cache
from django.db import connection
from django.db.models import Count, Max, Min, QuerySet

from .importer import FACETS_VERSION_KEY
from .models import Card
from .query import FIELDS

FACET_TTL = 60 * 60 * 24
SCHEMA = hashlib.sha1("|".join(f"{k}:{f.type}:{f.facet}" for k, f in FIELDS.items()).encode()).hexdigest()[:8]


def _array_counts(qs: QuerySet, column: str) -> list[dict]:
    ids_sql, params = qs.values("id").query.sql_with_params()
    table = Card._meta.db_table
    sql = (
        f'SELECT v, COUNT(*) AS n FROM {table} c, unnest(c."{column}") AS v '
        f"WHERE c.id IN ({ids_sql}) GROUP BY v ORDER BY n DESC, v"
    )
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return [{"value": v, "count": n} for v, n in cursor.fetchall()]


def _scalar_counts(qs: QuerySet, column: str) -> list[dict]:
    rows = (
        qs.exclude(**{f"{column}__isnull": True})
        .exclude(**{column: ""} if Card._meta.get_field(column).get_internal_type() in {"CharField", "TextField"} else {})
        .values(column).annotate(n=Count("id")).order_by("-n", column)
    )
    return [{"value": r[column], "count": r["n"]} for r in rows]


def compute_facets(qs: QuerySet, only: list[str] | None = None) -> dict:
    facets: dict[str, dict] = {}
    for key, f in FIELDS.items():
        if only and key not in only:
            continue
        column = f.columns[0]
        if f.type == "array" and f.facet:
            facets[key] = {"values": _array_counts(qs, column)}
        elif f.type == "enum" and f.facet:
            facets[key] = {"values": _scalar_counts(qs, column)}
        elif f.type == "number":
            agg = qs.aggregate(min=Min(column), max=Max(column))
            values = sorted(_scalar_counts(qs, column), key=lambda x: x["value"])
            facets[key] = {**agg, "values": values if len(values) <= 30 else []}
    return {"total": qs.count(), "facets": facets}


def cached_facets(qs: QuerySet, query_payload: dict | None = None, only: list[str] | None = None) -> dict:
    version = cache.get(FACETS_VERSION_KEY) or 0
    # Si cambian los campos filtrables (nuevo código), la caché antigua deja de valer sola
    digest = f"{SCHEMA}:" + hashlib.sha1(json.dumps([query_payload or {}, sorted(only or [])], sort_keys=True).encode()).hexdigest()[:16]
    key = f"facets:v{version}:{digest}"
    data = cache.get(key)
    if data is None:
        data = compute_facets(qs, only)
        cache.set(key, data, FACET_TTL if not query_payload else 300)
    return data
