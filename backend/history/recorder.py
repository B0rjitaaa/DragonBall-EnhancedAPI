"""Registrar acciones y deshacerlas.

Cada acción se envuelve en `record(...)`: se hace una foto de las tablas de la colección antes y otra después, y se
guarda solo lo que cambió (ActivityItem: antes / después por fila). Así da igual cómo escriba cada operación
(save, update, F(), borrados en cascada…): todo lo que cambia queda apuntado.

Deshacer devuelve esas filas a su «antes», pero solo si siguen como las dejó la acción; si alguna acción posterior
las cambió, se avisa (UndoConflict) con esas acciones para deshacerlas primero.

Las acciones van de una en una (un candado de Postgres): una foto no puede mezclar dos acciones a la vez.
"""
from __future__ import annotations

import contextvars
import json
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import timedelta

from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection, transaction
from django.utils import timezone

from collection.models import CollectionEntry, Location, StatusChange
from decks.models import DeckVersion, DeckVersionCard, Match, PickList, SideCard

from .models import Activity, ActivityItem, RestorePoint

LOCK_KEY = 7_311_002  # pg_advisory_xact_lock: una acción registrada a la vez
# Clics seguidos sobre lo mismo (misma group_key) dentro de este margen: una sola acción.
GROUP_WINDOW = {"adjust": timedelta(seconds=90), "note": timedelta(seconds=90), "reorder": timedelta(seconds=90),
                "scan": timedelta(minutes=20)}
RESTORE_POINT_DAYS = 90


@dataclass(frozen=True)
class Spec:
    """Una tabla que se sigue: su nombre corto, el modelo, la clave de cada fila y los campos que se guardan."""

    name: str
    model: type
    key: tuple[str, ...]
    fields: tuple[str, ...]
    card: str | None = None  # campo con la carta (para filtrar por carta)
    location: str | None = None  # campo con la ubicación / mazo


# Orden: primero los «padres» (ubicaciones, versiones), luego lo que cuelga de ellos.
SPECS: tuple[Spec, ...] = (
    Spec("location", Location, ("id",), ("uid", "name", "kind", "status", "parked_at", "notes", "binder_rows",
                                         "binder_cols", "binder_pages", "is_default", "position", "created_at"),
         location="id"),
    Spec("version", DeckVersion, ("id",), ("deck_id", "number", "name", "notes", "automatic", "principal", "created_at"),
         location="deck_id"),
    Spec("entry", CollectionEntry, ("card_id", "location_id", "fake"), ("quantity", "notes", "position", "created_at"),
         card="card_id", location="location_id"),
    Spec("side", SideCard, ("deck_id", "card_id"), ("quantity",), card="card_id", location="deck_id"),
    Spec("version_card", DeckVersionCard, ("version_id", "card_id", "section"), ("quantity",), card="card_id"),
    Spec("pick_list", PickList, ("deck_id",), ("groups", "created_at"), location="deck_id"),
    Spec("status_change", StatusChange, ("id",), ("location_id", "status", "at", "copies"), location="location_id"),
    Spec("match", Match, ("id",), ("version_id", "played_on", "opponent_leader_bandai_id", "opponent_leader_name",
                                   "opponent_name", "result", "went_first", "score", "event", "notes", "created_at")),
)
SPEC = {s.name: s for s in SPECS}
# Campos que no se comparan al deshacer (no cambian solos, pero tampoco deben bloquear un «Undo»).
CREATED_FIELDS = {"created_at"}

Snapshot = dict[str, dict[str, dict]]


def _plain(values: dict) -> dict:
    """Valores en tipos de JSON (fechas e ids en texto), igual que se guardan: así se pueden comparar."""
    return json.loads(json.dumps(values, cls=DjangoJSONEncoder))


def _key_str(key: list) -> str:
    return json.dumps(key)


def snapshot() -> Snapshot:
    """Todas las filas de las tablas seguidas: {tabla: {clave: valores}}."""
    out: Snapshot = {}
    for spec in SPECS:
        rows = spec.model.objects.values(*spec.key, *spec.fields)
        table = {}
        for row in rows:
            row = _plain(row)
            key = [row.pop(k) for k in spec.key]
            table[_key_str(key)] = row
        out[spec.name] = table
    return out


def diff(before: Snapshot, after: Snapshot) -> list[dict]:
    items = []
    for spec in SPECS:
        old, new = before.get(spec.name, {}), after.get(spec.name, {})
        for k in old.keys() | new.keys():
            a, b = old.get(k), new.get(k)
            if a != b:
                items.append({"model": spec.name, "key": json.loads(k), "before": a, "after": b})
    return items


def _refs(model: str, key: list, values: dict | None, other: dict | None) -> tuple[int | None, int | None]:
    """La carta y la ubicación de una fila (para filtrar el histórico)."""
    spec = SPEC[model]
    row = {**dict(zip(spec.key, key)), **(values or other or {})}
    card = row.get(spec.card) if spec.card else None
    loc = row.get(spec.location) if spec.location else None
    if model == "version_card":
        version = DeckVersion.objects.filter(pk=row["version_id"]).values_list("deck_id", flat=True).first()
        loc = version
    if model == "match":
        loc = DeckVersion.objects.filter(pk=row["version_id"]).values_list("deck_id", flat=True).first()
    return card, loc


def _lock() -> None:
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [LOCK_KEY])


@dataclass
class Recording:
    kind: str
    title: str = ""
    source: str = Activity.Source.WEB
    group_key: str = ""
    restore_point: bool = False
    undo_of: Activity | None = None
    activity: Activity | None = None
    extra: dict = field(default_factory=dict)


_current: contextvars.ContextVar[Recording | None] = contextvars.ContextVar("history_recording", default=None)


def describe(title: str) -> None:
    """Pone el título de la acción que se está registrando (si aún no tiene)."""
    rec = _current.get()
    if rec is not None and not rec.title:
        rec.title = title[:300]


@contextmanager
def record(kind: str, title: str = "", source: str = Activity.Source.WEB, group_key: str = "",
           restore_point: bool = False):
    """Registra como una acción todo lo que cambie dentro del bloque. Dentro de otra acción no hace nada aparte."""
    if _current.get() is not None:
        yield _current.get()
        return
    rec = Recording(kind=kind, title=title, source=source, group_key=group_key, restore_point=restore_point)
    token = _current.set(rec)
    try:
        with transaction.atomic():
            _lock()
            before = snapshot()
            yield rec
            items = diff(before, snapshot())
            if items:
                rec.activity = _save(rec, items, before)
    finally:
        _current.reset(token)


def recorded(kind: str, source: str = Activity.Source.WEB, group_key=None, restore_point: bool = False):
    """Decorador de vistas: registra la petición como una acción (group_key puede ser una función de la petición)."""

    def deco(fn):
        def wrapper(view, request, *args, **kwargs):
            key = group_key(request, *args, **kwargs) if callable(group_key) else (group_key or "")
            with record(kind, source=source, group_key=key, restore_point=restore_point):
                return fn(view, request, *args, **kwargs)

        wrapper.__name__ = fn.__name__
        wrapper.__doc__ = fn.__doc__
        return wrapper

    return deco


def _save(rec: Recording, items: list[dict], before: Snapshot) -> Activity:
    now = timezone.now()
    prefix = rec.group_key.split(":", 1)[0]
    window = GROUP_WINDOW.get(prefix)
    if rec.group_key and window:
        last = Activity.objects.order_by("-updated_at", "-id").first()
        if (last and last.group_key == rec.group_key and last.undone_at is None and last.undo_of_id is None
                and now - last.updated_at <= window):
            _merge(last, items)
            last.updated_at = now
            if not last.custom_title:
                last.title = auto_title(last.kind, list(last.items.all()))
            last.save(update_fields=["updated_at", "title"])
            return last
    activity = Activity.objects.create(kind=rec.kind, title=rec.title[:300] or "…", custom_title=bool(rec.title), source=rec.source,
                                       group_key=rec.group_key, created_at=now, updated_at=now, undo_of=rec.undo_of)
    _add_items(activity, items)
    if not rec.title:
        activity.title = auto_title(activity.kind, list(activity.items.all()))
        activity.save(update_fields=["title"])
    if rec.restore_point:
        RestorePoint.objects.create(created_at=now, reason=activity.title, activity=activity, snapshot=before)
    return activity


def _add_items(activity: Activity, items: list[dict]) -> None:
    ActivityItem.objects.bulk_create(
        ActivityItem(activity=activity, model=i["model"], key=i["key"], before=i["before"], after=i["after"],
                     card_id=(refs := _refs(i["model"], i["key"], i["after"], i["before"]))[0], location_id=refs[1])
        for i in items
    )


def _merge(activity: Activity, items: list[dict]) -> None:
    """Suma a una acción los cambios de otra seguida: cada fila conserva su «antes» y toma el nuevo «después»."""
    existing = {(i.model, _key_str(i.key)): i for i in activity.items.all()}
    new = []
    for item in items:
        old = existing.get((item["model"], _key_str(item["key"])))
        if old is None:
            new.append(item)
        elif old.before == item["after"]:
            old.delete()  # vuelve a estar como al principio
        else:
            old.after = item["after"]
            old.save(update_fields=["after"])
    _add_items(activity, new)


# --- Deshacer ---------------------------------------------------------------------------------------------------


class UndoConflict(Exception):
    """Algunas filas ya no están como las dejó la acción: estas acciones posteriores las cambiaron."""

    def __init__(self, later: list[Activity], rows: int):
        super().__init__(f"{rows} changes were modified later")
        self.later = later
        self.rows = rows


def _current_row(spec: Spec, key: list) -> dict | None:
    row = spec.model.objects.filter(**dict(zip(spec.key, key))).values(*spec.fields).first()
    return _plain(row) if row is not None else None


def _same(a: dict | None, b: dict | None) -> bool:
    if a is None or b is None:
        return a is b
    return {k: v for k, v in a.items() if k not in CREATED_FIELDS} == {k: v for k, v in b.items() if k not in CREATED_FIELDS}


def conflicts(activity: Activity) -> tuple[list[Activity], int]:
    """Filas de la acción que ya no están como las dejó, y las acciones posteriores (sin deshacer) que las tocaron."""
    bad = [i for i in activity.items.all() if not _same(_current_row(SPEC[i.model], i.key), i.after)]
    if not bad:
        return [], 0
    later = set()
    for i in bad:
        later |= set(ActivityItem.objects.filter(activity__updated_at__gte=activity.created_at, model=i.model, key=i.key)
                     .exclude(activity=activity).values_list("activity_id", flat=True))
    acts = list(Activity.objects.filter(id__in=later, undone_at__isnull=True).order_by("-updated_at"))
    return acts, len(bad)


def _apply(targets: list[tuple[str, list, dict | None]]) -> None:
    """Deja cada fila como `target` (None = que no exista). Primero borra (de hijos a padres) y luego crea o
    actualiza (de padres a hijos; las versiones que dejan de ser principales antes que la nueva principal)."""
    order = {s.name: n for n, s in enumerate(SPECS)}
    deletes = sorted((t for t in targets if t[2] is None), key=lambda t: -order[t[0]])
    for model, key, _ in deletes:
        spec = SPEC[model]
        spec.model.objects.filter(**dict(zip(spec.key, key))).delete()
    upserts = sorted((t for t in targets if t[2] is not None),
                     key=lambda t: (order[t[0]], bool(t[2].get("principal")) if t[0] == "version" else False))
    for model, key, values in upserts:
        spec = SPEC[model]
        lookup = dict(zip(spec.key, key))
        qs = spec.model.objects.filter(**lookup)
        if not qs.exists():
            obj = spec.model(**lookup, **values)
            if model == "pick_list":
                obj.done = []
            spec.model.objects.bulk_create([obj])
        # update(): sin save(), así se conservan las fechas de creación y no se recalcula nada.
        spec.model.objects.filter(**lookup).update(**values)


def preview_undo(activity: Activity) -> dict:
    later, rows = conflicts(activity)
    return {"ok": not later and not rows, "conflict_rows": rows, "later": later}


def undo(activity: Activity, source: str = Activity.Source.WEB) -> Activity | None:
    """Deshace la acción (como una acción nueva, «Undo: …»). UndoConflict si algo se cambió después."""
    if activity.undone_at is not None:
        raise ValueError("This change was already undone")
    with record("undo", title=f"Undo: {activity.title}"[:300], source=source) as rec:
        rec.undo_of = activity
        later, rows = conflicts(activity)
        if rows:
            raise UndoConflict(later, rows)
        _apply([(i.model, i.key, i.before) for i in activity.items.all()])
        Activity.objects.filter(pk=activity.pk).update(undone_at=timezone.now())
    return rec.activity


# --- Puntos de restauración -------------------------------------------------------------------------------------


def restore_point_changes(point: RestorePoint) -> list[dict]:
    """Lo que cambiaría al volver al punto: filas de ahora frente a las de la foto."""
    return diff(snapshot(), point.snapshot)


def restore_to_point(point: RestorePoint, source: str = Activity.Source.WEB) -> Activity | None:
    with record("restore_point", title=f"Went back to before: {point.reason}"[:300], source=source,
                restore_point=True) as rec:
        rec.undo_of = point.activity
        changes = diff(snapshot(), point.snapshot)
        _apply([(c["model"], c["key"], c["after"]) for c in changes])
    return rec.activity


def purge_restore_points() -> int:
    deleted, _ = RestorePoint.objects.filter(created_at__lt=timezone.now() - timedelta(days=RESTORE_POINT_DAYS)).delete()
    return deleted


# --- Títulos ------------------------------------------------------------------------------------------------------

KIND_LABELS = {
    "adjust": "Copies", "move": "Moved copies", "note": "Note", "reorder": "Reordered", "location": "Location",
    "location_delete": "Deleted location", "binder": "Binder", "csv_import": "Imported CSV", "restore": "Restored backup",
    "deck_import": "Imported deck", "deck_version": "Deck list", "deck_restore": "Made a list the main one",
    "deck_side": "Side deck", "deck_archive": "Archived deck", "deck_back": "Deck back in use",
    "deck_missing": "Missing cards", "scan": "Scanner", "admin": "Admin", "price_review": "Price review",
    "undo": "Undo", "restore_point": "Restore point",
}


def copy_moves(items) -> tuple[dict[int, dict[int, int]], int, int]:
    """Por carta, cuántas copias cambian en cada ubicación; y el total que entra y sale de la colección."""
    per_card: dict[int, dict[int, int]] = {}
    added = removed = 0
    for i in items:
        if i.model != "entry":
            continue
        delta = (i.after or {}).get("quantity", 0) - (i.before or {}).get("quantity", 0)
        if delta:
            card, loc = i.key[0], i.key[1]
            per_card.setdefault(card, {})
            per_card[card][loc] = per_card[card].get(loc, 0) + delta
    for locs in per_card.values():
        net = sum(locs.values())
        if net > 0:
            added += net
        else:
            removed -= net
    return per_card, added, removed


def auto_title(kind: str, items) -> str:
    """Un título a partir de lo que cambió, cuando la acción no trae uno: primero lo que no son copias (ubicaciones,
    listas, side…) y luego las copias («+2 BT1-073 → Caja 1», «2× BT1-073 Caja 1 → Payaso», «+5 copies · 3 moved»)."""
    from cards.models import Card

    from .views import _card_info, _location_names, _other_changes

    label = KIND_LABELS.get(kind, kind)
    names = _location_names(items)
    per_card, added, removed = copy_moves(items)
    parts: list[str] = []
    other = [i for i in items if i.model != "entry"]
    if other:
        phrases = _other_changes(other, names, _card_info({i.card_id for i in other if i.card_id}))
        if phrases:
            parts.append(phrases[0] + (f" (+{len(phrases) - 1} more)" if len(phrases) > 1 else ""))
    if len(per_card) == 1:
        card_id, locs = next(iter(per_card.items()))
        card = Card.objects.filter(pk=card_id).values_list("card_number", flat=True).first() or f"#{card_id}"
        gone = [names.get(l, "?") for l, d in locs.items() if d < 0]
        came = [names.get(l, "?") for l, d in locs.items() if d > 0]
        net = sum(locs.values())
        if net == 0 and gone and came:
            parts.append(f"{max(locs.values())}× {card} {', '.join(gone)} → {', '.join(came)}")
        else:
            parts.append(f"{'+' if net > 0 else '−'}{abs(net)} {card} {'→' if net > 0 else 'from'} "
                         f"{', '.join(came if net > 0 else gone)}")
    elif per_card:
        if added:
            parts.append(f"+{added} copies")
        if removed:
            parts.append(f"−{removed} copies")
        moved = sum(max(0, d) for locs in per_card.values() if sum(locs.values()) == 0 for d in locs.values())
        if moved:
            parts.append(f"{moved} moved")
    if not parts:
        parts.append("positions and notes" if any(i.model == "entry" for i in items) else "changes")
    return f"{label}: {' · '.join(parts)}"[:300]
