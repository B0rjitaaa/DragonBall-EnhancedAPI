"""Restaurar Mi colección desde la copia JSON de «Descargar copia» (format dbs-collection), SUSTITUYENDO
las copias actuales por las de la copia.

- La vista previa y la aplicación salen del mismo plan (`plan`), así que lo que se ve es lo que se hace.
- Las ubicaciones se emparejan por nombre (sin tildes ni mayúsculas); las que faltan se crean con su tipo
  y notas. Las que no están en la copia no se borran: se quedan vacías (así los mazos conservan sus
  versiones y partidas, que no van en la copia).
- Las cartas que no están en el catálogo se saltan (y se avisa).
- Las copias que siguen donde estaban conservan su sitio en «Mi orden»; las nuevas van al final.
- Todo en una transacción: o se aplica entero o nada.
"""
from __future__ import annotations

import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field

from django.db import transaction
from django.db.models import Max

from cards.models import Card
from decks.models import SideCard

from .models import OLD_DEFAULT_LOCATION_NAME, CollectionEntry, Location

FORMAT = "dbs-collection"
KINDS = {"deck": Location.Kind.DECK, "binder": Location.Kind.BINDER, "storage": Location.Kind.STORAGE,
         "other": Location.Kind.OTHER,
         # Copias anteriores (en español)
         "mazo": Location.Kind.DECK, "archivador": Location.Kind.BINDER, "almacén": Location.Kind.STORAGE,
         "almacen": Location.Kind.STORAGE, "otro": Location.Kind.OTHER}
MAX_CHANGES = 300  # cambios carta a carta que se listan en la vista previa


class RestoreError(ValueError):
    pass


def _key(name: str) -> str:
    plain = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode()
    return plain.strip().lower()


@dataclass
class Plan:
    # (card_id, clave de ubicación, falsa) → [cantidad, notas]
    target: dict = field(default_factory=dict)
    # clave de ubicación → nombre mostrado, y las que hay que crear (clave → {name, kind, notes})
    names: dict = field(default_factory=dict)
    create: dict = field(default_factory=dict)
    skipped: list = field(default_factory=list)


def _plan(doc: dict) -> Plan:
    if not isinstance(doc, dict) or doc.get("format") != FORMAT:
        raise RestoreError("This is not a My collection backup (missing \"format\": \"dbs-collection\")")
    cards_in = doc.get("cards")
    if not isinstance(cards_in, list):
        raise RestoreError("The backup has no card list")
    plan = Plan()
    existing = {_key(loc.name): loc for loc in Location.objects.all()}
    default = Location.default()
    for key, loc in existing.items():
        plan.names[key] = loc.name
    default_key = _key(default.name)
    # Copias anteriores: la ubicación por defecto se llamaba «Sin ubicar».
    aliases = {} if _key(OLD_DEFAULT_LOCATION_NAME) in existing else {_key(OLD_DEFAULT_LOCATION_NAME): default_key}
    for place in doc.get("locations") or []:
        name = str(place.get("name") or "").strip()[:80]
        key = aliases.get(_key(name), _key(name))
        if not name or key in existing or key in plan.create:
            continue
        plan.create[key] = {"name": name, "kind": KINDS.get(_key(place.get("kind", "")), Location.Kind.OTHER),
                            "notes": str(place.get("notes") or "")}
        plan.names[key] = name
    known = set(Card.objects.filter(id__in=[r.get("id") for r in cards_in if isinstance(r, dict)])
                .values_list("id", flat=True))
    for row in cards_in:
        if not isinstance(row, dict):
            continue
        card_id, qty = row.get("id"), row.get("qty")
        label = f"{row.get('number') or card_id} {row.get('name') or ''}".strip()
        if card_id not in known:
            plan.skipped.append({"card": label, "reason": "not in the catalog"})
            continue
        if not isinstance(qty, int) or qty < 1:
            plan.skipped.append({"card": label, "reason": f"invalid quantity: {qty!r}"})
            continue
        name = str(row.get("location") or "").strip()
        key = aliases.get(_key(name), _key(name)) if name else default_key
        if key not in plan.names:  # ubicación que no viene en la lista de la copia: se crea igual
            plan.create[key] = {"name": name[:80], "kind": Location.Kind.OTHER, "notes": ""}
            plan.names[key] = name[:80]
        slot = plan.target.setdefault((card_id, key, bool(row.get("fake"))), [0, ""])
        slot[0] += qty
        notes = str(row.get("notes") or "")
        if notes and notes not in slot[1]:
            slot[1] = f"{slot[1]}\n{notes}".strip()
    return plan


def _current() -> dict:
    """(card_id, clave de ubicación, falsa) → cantidad, de la colección actual."""
    return {
        (e.card_id, _key(e.location.name), e.fake): e.quantity
        for e in CollectionEntry.objects.select_related("location")
    }


def preview(doc: dict) -> dict:
    plan = _plan(doc)
    now = _current()
    after = {k: v[0] for k, v in plan.target.items()}
    keys = set(now) | set(after)
    cards = {c.id: c for c in Card.objects.filter(id__in={k[0] for k in keys}).only("id", "card_number", "name")}
    changes = []
    for k in sorted(keys, key=lambda k: (plan.names.get(k[1], k[1]), cards[k[0]].card_number, k[2])):
        before, later = now.get(k, 0), after.get(k, 0)
        if before != later:
            card = cards[k[0]]
            changes.append({"card_id": card.id, "number": card.card_number, "name": card.name,
                            "location": plan.names.get(k[1], k[1]), "fake": k[2], "before": before, "after": later})
    per_loc = defaultdict(lambda: [0, 0])
    for (_, loc, _), q in now.items():
        per_loc[loc][0] += q
    for (_, loc, _), q in after.items():
        per_loc[loc][1] += q
    locations = [{"name": plan.names.get(k, k), "before": b, "after": a, "new": k in plan.create}
                 for k, (b, a) in sorted(per_loc.items(), key=lambda kv: plan.names.get(kv[0], kv[0])) if b != a]
    return {
        "exported_at": doc.get("exported_at"),
        "before": {"copies": sum(now.values()), "cards": len({k[0] for k in now})},
        "after": {"copies": sum(after.values()), "cards": len({k[0] for k in after}),
                  "fakes": sum(q for k, q in after.items() if k[2])},
        "added": sum(max(c["after"] - c["before"], 0) for c in changes),
        "removed": sum(max(c["before"] - c["after"], 0) for c in changes),
        "create_locations": [v["name"] for v in plan.create.values()],
        "emptied_locations": [plan.names.get(k, k) for k, (b, a) in per_loc.items() if b and not a],
        "locations": locations,
        "changes": changes[:MAX_CHANGES],
        "changes_total": len(changes),
        "skipped": plan.skipped,
    }


def apply(doc: dict) -> dict:
    plan = _plan(doc)
    with transaction.atomic():
        locations = {_key(loc.name): loc for loc in Location.objects.select_for_update()}
        top = Location.objects.aggregate(m=Max("position"))["m"] or 0
        for key, data in plan.create.items():
            top += 1
            locations[key] = Location.objects.create(position=top, **data)
        # Sitio en «Mi orden» de lo que ya estaba (las filas auténtica y falsa comparten posición).
        positions = {(e.card_id, e.location_id): e.position for e in CollectionEntry.objects.all()}
        CollectionEntry.objects.all().delete()  # los escaneos que apuntaban a ellas se quedan sin enlace (SET_NULL)
        last = defaultdict(int)
        for (card_id, loc_id), pos in positions.items():
            last[loc_id] = max(last[loc_id], pos)
        rows = []
        for (card_id, key, fake), (qty, notes) in sorted(plan.target.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            loc = locations[key]
            pos = positions.get((card_id, loc.id))
            if pos is None:
                last[loc.id] += 1
                pos = positions[(card_id, loc.id)] = last[loc.id]
            rows.append(CollectionEntry(card_id=card_id, location=loc, fake=fake, quantity=qty, notes=notes,
                                        position=pos))
        CollectionEntry.objects.bulk_create(rows, batch_size=1000)
        # El side deck no puede tener más copias de las que hay en el mazo.
        copies = defaultdict(int)
        for e in rows:
            copies[(e.location_id, e.card_id)] += e.quantity
        for side in SideCard.objects.all():
            have = copies.get((side.deck_id, side.card_id), 0)
            if have == 0:
                side.delete()
            elif side.quantity > have:
                side.quantity = have
                side.save(update_fields=["quantity"])
    return {"copies": sum(e.quantity for e in rows), "rows": len(rows), "created_locations": len(plan.create),
            "skipped": len(plan.skipped)}
