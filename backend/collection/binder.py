"""Vista de archivador: dónde está cada copia de un Binder (página y bolsillo) y moverlas o reordenar páginas.

La posición de cada copia vive en la nota de su fila de la colección: una línea por copia, «P. 12 · row 2 ·
col 3» (o la antigua «Pág. 12 · fila 2 · col 3»), la misma que escribe el modo archivador del escáner. Así lo
que ya usa esas notas (mover copias, lista de recogida, copia de seguridad) sigue funcionando: aquí solo se
leen y se reescriben. Las líneas que no son posiciones se conservan tal cual.

Un bolsillo se numera de 1 a filas×columnas, por filas. Las copias sin posición (o con una posición que no
cabe en el archivador, o repetida) salen como «sin colocar».
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from django.db import transaction

from .models import CollectionEntry, Location

POSITION = re.compile(r"^\s*P(?:ág)?\.?\s*(\d+)\s*·\s*(?:row|fila)\s*(\d+)\s*·\s*col\s*(\d+)\s*$", re.I)
MAX_PAGES = 999


class BinderError(Exception):
    pass


def position_line(page: int, row: int, col: int) -> str:
    return f"P. {page} · row {row} · col {col}"


@dataclass
class _Row:
    entry: CollectionEntry
    other_lines: list[str] = field(default_factory=list)
    # (página, bolsillo) de cada copia colocada
    spots: list[tuple[int, int]] = field(default_factory=list)


@dataclass
class Layout:
    binder: Location
    rows: list[_Row]
    # (página, bolsillo) → la fila que lo ocupa
    slots: dict[tuple[int, int], _Row]

    @property
    def pockets(self) -> int:
        return self.binder.binder_rows * self.binder.binder_cols

    @property
    def pages(self) -> int:
        used = max((page for page, _slot in self.slots), default=0)
        return max(self.binder.binder_pages, used, 1)


def _binder(location_id: int, lock: bool = False) -> Location:
    qs = Location.objects.filter(pk=location_id, kind=Location.Kind.BINDER)
    if lock:
        qs = qs.select_for_update()
    binder = qs.first()
    if binder is None:
        raise BinderError("That binder doesn't exist")
    return binder


def layout(binder: Location, lock: bool = False) -> Layout:
    """Lee las posiciones de las notas. Por fila, como mucho tantas posiciones como copias tiene."""
    entries = CollectionEntry.objects.filter(location=binder).select_related("card").order_by("card__card_number", "card_id", "fake")
    if lock:
        entries = entries.select_for_update()
    pockets = binder.binder_rows * binder.binder_cols
    rows, slots = [], {}
    for entry in entries:
        row = _Row(entry)
        for line in (entry.notes or "").splitlines():
            m = POSITION.match(line)
            if not m:
                if line.strip():
                    row.other_lines.append(line)
                continue
            page, r, c = (int(x) for x in m.groups())
            slot = (r - 1) * binder.binder_cols + c
            valid = 1 <= r <= binder.binder_rows and 1 <= c <= binder.binder_cols and 1 <= page <= MAX_PAGES
            if valid and len(row.spots) < entry.quantity and (page, slot) not in slots:
                row.spots.append((page, slot))
                slots[(page, slot)] = row
            # Si no cabe, está repetida o sobra (más líneas que copias), esa copia queda sin colocar.
        rows.append(row)
    return Layout(binder, rows, slots)


def data(location_id: int) -> dict:
    """La vista: tamaño, páginas, qué hay en cada bolsillo y lo que está sin colocar."""
    lay = layout(_binder(location_id))
    b = lay.binder
    return {
        "binder": {"id": b.pk, "uid": str(b.uid), "name": b.name, "rows": b.binder_rows, "cols": b.binder_cols},
        "pages": lay.pages,
        "slots": [
            {"page": page, "slot": slot, "bandai_id": row.entry.card_id, "fake": row.entry.fake}
            for (page, slot), row in sorted(lay.slots.items())
        ],
        "unplaced": [
            {"bandai_id": row.entry.card_id, "fake": row.entry.fake, "quantity": row.entry.quantity - len(row.spots)}
            for row in lay.rows if row.entry.quantity > len(row.spots)
        ],
        "copies": sum(row.entry.quantity for row in lay.rows),
    }


def _save(lay: Layout, rows: set[int] | None = None) -> None:
    """Reescribe las notas: las líneas que no son posiciones y, detrás, las posiciones en orden."""
    cols = lay.binder.binder_cols
    for row in lay.rows:
        if rows is not None and row.entry.pk not in rows:
            continue
        lines = list(row.other_lines)
        for page, slot in sorted(row.spots):
            lines.append(position_line(page, (slot - 1) // cols + 1, (slot - 1) % cols + 1))
        notes = "\n".join(lines)
        if notes != row.entry.notes:
            CollectionEntry.objects.filter(pk=row.entry.pk).update(notes=notes)


def _check_spot(lay: Layout, page, slot) -> tuple[int, int]:
    try:
        page, slot = int(page), int(slot)
    except (TypeError, ValueError):
        raise BinderError("Say which page and pocket") from None
    if not 1 <= page <= lay.pages or not 1 <= slot <= lay.pockets:
        raise BinderError("That pocket isn't in the binder")
    return page, slot


def move(location_id: int, source: dict, target: dict | None) -> dict:
    """Mueve una copia: de un bolsillo (`{page, slot}`) o de lo sin colocar (`{bandai_id, fake}`) a otro bolsillo
    (si está ocupado, se intercambian; si la copia venía de lo sin colocar, la que estaba pasa a sin colocar) o,
    con `target=None`, la saca a lo sin colocar."""
    with transaction.atomic():
        lay = layout(_binder(location_id, lock=True), lock=True)
        if "page" in source:
            src_spot = _check_spot(lay, source.get("page"), source.get("slot"))
            mover = lay.slots.get(src_spot)
            if mover is None:
                raise BinderError("That pocket is empty")
        else:
            src_spot = None
            mover = next(
                (r for r in lay.rows if r.entry.card_id == source.get("bandai_id") and r.entry.fake == bool(source.get("fake"))
                 and r.entry.quantity > len(r.spots)),
                None,
            )
            if mover is None:
                raise BinderError("There's no copy of that card left to place")
        touched = {mover.entry.pk}
        if target is None:
            if src_spot is not None:
                mover.spots.remove(src_spot)
        else:
            dst_spot = _check_spot(lay, target.get("page"), target.get("slot"))
            if dst_spot == src_spot:
                return data(location_id)
            occupant = lay.slots.get(dst_spot)
            if src_spot is not None:
                mover.spots.remove(src_spot)
            if occupant is not None:
                touched.add(occupant.entry.pk)
                occupant.spots.remove(dst_spot)
                if src_spot is not None:  # intercambio
                    occupant.spots.append(src_spot)
            mover.spots.append(dst_spot)
        _save(lay, touched)
    return data(location_id)


def _remap(lay: Layout, page_map) -> None:
    for row in lay.rows:
        row.spots = [(page_map(page), slot) for page, slot in row.spots]


def insert_page(location_id: int, page: int) -> dict:
    """Mete una página vacía en `page`: esa y las siguientes se corren una."""
    with transaction.atomic():
        binder = _binder(location_id, lock=True)
        lay = layout(binder, lock=True)
        total = lay.pages
        if not 1 <= page <= total + 1:
            raise BinderError("That page isn't in the binder")
        if total >= MAX_PAGES:
            raise BinderError(f"A binder can have up to {MAX_PAGES} pages")
        _remap(lay, lambda p: p + 1 if p >= page else p)
        _save(lay)
        Location.objects.filter(pk=binder.pk).update(binder_pages=total + 1)
    return data(location_id)


def delete_page(location_id: int, page: int) -> dict:
    """Quita una página vacía: las siguientes se corren una hacia atrás."""
    with transaction.atomic():
        binder = _binder(location_id, lock=True)
        lay = layout(binder, lock=True)
        total = lay.pages
        if not 1 <= page <= total:
            raise BinderError("That page isn't in the binder")
        if any(p == page for p, _slot in lay.slots):
            raise BinderError("Only empty pages can be removed: move its cards first")
        if total <= 1:
            raise BinderError("A binder needs at least one page")
        _remap(lay, lambda p: p - 1 if p > page else p)
        _save(lay)
        Location.objects.filter(pk=binder.pk).update(binder_pages=total - 1)
    return data(location_id)


def move_page(location_id: int, page: int, to: int) -> dict:
    """Lleva la página `page`, con sus cartas, a la posición `to`; las de en medio se corren."""
    with transaction.atomic():
        binder = _binder(location_id, lock=True)
        lay = layout(binder, lock=True)
        total = lay.pages
        if not (1 <= page <= total and 1 <= to <= total):
            raise BinderError("That page isn't in the binder")
        if page != to:
            order = list(range(1, total + 1))
            order.insert(to - 1, order.pop(page - 1))
            new_number = {old: new for new, old in enumerate(order, start=1)}
            _remap(lay, lambda p: new_number[p])
            _save(lay)
        Location.objects.filter(pk=binder.pk).update(binder_pages=total)
    return data(location_id)
