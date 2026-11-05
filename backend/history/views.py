"""API del histórico (página Tools → History, la ficha de una carta y la vista de un mazo)."""
from datetime import datetime

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from cards.models import Card
from cards.thumbs import thumb_url
from collection.models import Location

from . import recorder
from .models import Activity, ActivityItem, RestorePoint

PAGE_SIZE = 30


def _location_names(items) -> dict[int, str]:
    """Nombres de las ubicaciones que salen en los cambios (también las borradas, por su «antes»)."""
    ids = {i.key[1] for i in items if i.model == "entry"} | {i.location_id for i in items if i.location_id}
    names = dict(Location.objects.filter(id__in=ids).values_list("id", "name"))
    for i in items:
        if i.model == "location":
            for values in (i.after, i.before):
                if values and values.get("name"):
                    names.setdefault(i.key[0], values["name"])
    return names


def _summary(activity: Activity, items) -> dict:
    per_card, added, removed = recorder.copy_moves(items)
    moved = sum(max(0, d) for locs in per_card.values() if sum(locs.values()) == 0 for d in locs.values())
    names = _location_names(items)
    locations = sorted({names.get(loc, "?") for locs in per_card.values() for loc in locs}
                       | {names.get(i.location_id, "?") for i in items if i.location_id and i.model != "entry"})
    point = getattr(activity, "restore_point", None)
    return {
        "id": activity.id,
        "kind": activity.kind,
        "kind_label": recorder.KIND_LABELS.get(activity.kind, activity.kind),
        "title": activity.title,
        "source": activity.source,
        "created_at": activity.created_at,
        "updated_at": activity.updated_at,
        "undone_at": activity.undone_at,
        "undo_of": {"id": activity.undo_of_id, "title": activity.undo_of.title} if activity.undo_of_id else None,
        "restore_point": point.id if point else None,
        "added": added,
        "removed": removed,
        "moved": moved,
        "cards": len(per_card),
        "locations": [n for n in locations if n != "?"][:8],
    }


def _card_info(ids) -> dict[int, dict]:
    rows = Card.objects.filter(id__in=ids).values("id", "card_number", "name", "image_url")
    return {c["id"]: {**c, "thumb_url": thumb_url(c["id"], c["image_url"])} for c in rows}


def _other_changes(items, names: dict[int, str], cards: dict[int, dict]) -> list[str]:
    """Lo que no son copias, en frases: ubicaciones, listas de mazos, side, archivar…"""
    out = []
    versions = {i.key[0]: (i.after or i.before) for i in items if i.model == "version"}

    def deck(loc_id):
        return f"“{names.get(loc_id, '?')}”"

    def card(card_id):
        c = cards.get(card_id)
        return f"{c['card_number']} {c['name']}" if c else f"#{card_id}"

    for i in items:
        b, a = i.before, i.after
        if i.model == "location":
            if b is None:
                if not a.get("is_default"):  # «Unsorted» se crea sola cuando hace falta: no es noticia
                    out.append(f"Created {a['kind']} “{a['name']}”")
            elif a is None:
                out.append(f"Deleted {b['kind']} “{b['name']}”")
            else:
                if b["name"] != a["name"]:
                    out.append(f"Renamed “{b['name']}” → “{a['name']}”")
                if b["status"] != a["status"]:
                    out.append(f"{'Archived' if a['status'] == 'parked' else 'Back in use'}: “{a['name']}”")
                if (b["binder_pages"], b["binder_rows"], b["binder_cols"]) != (a["binder_pages"], a["binder_rows"], a["binder_cols"]):
                    out.append(f"“{a['name']}”: binder layout {b['binder_pages']} → {a['binder_pages']} pages")
                if b["position"] != a["position"] and b["name"] == a["name"]:
                    out.append(f"“{a['name']}”: moved in the list of locations")
                if b["notes"] != a["notes"]:
                    out.append(f"“{a['name']}”: notes changed")
        elif i.model == "version":
            v = a or b
            label = f"{deck(v['deck_id'])} v{v['number']}"
            if b is None:
                out.append(f"{label}: new list{' (main)' if a['principal'] else ''}")
            elif a is None:
                out.append(f"{label}: list removed")
            elif b["principal"] != a["principal"]:
                out.append(f"{label}: {'now the main list' if a['principal'] else 'no longer the main list'}")
            elif (b["name"], b["notes"]) != (a["name"], a["notes"]):
                out.append(f"{label}: name or notes changed")
        elif i.model == "side":
            out.append(f"Side deck of {deck(i.key[0])}: {card(i.key[1])} {(b or {}).get('quantity', 0)} → {(a or {}).get('quantity', 0)}")
        elif i.model == "version_card":
            v = versions.get(i.key[0])
            if v is None:  # cambio de cartas en una versión que ya existía (p. ej. quitar una «missing»)
                out.append(f"List: {card(i.key[1])} ({i.key[2]}) {(b or {}).get('quantity', 0)} → {(a or {}).get('quantity', 0)}")
        elif i.model == "pick_list":
            out.append(f"Pick list of {deck(i.key[0])} {'saved' if a else 'removed'}")
        elif i.model == "match":
            out.append(f"Match {'removed' if a is None else 'restored' if b is None else 'changed'}")
    return out


def _detail(activity: Activity) -> dict:
    items = list(activity.items.all())
    names = _location_names(items)
    per_card: dict[int, list[dict]] = {}
    for i in items:
        if i.model != "entry":
            continue
        card_id, loc, fake = i.key
        per_card.setdefault(card_id, []).append({
            "location_id": loc, "location": names.get(loc, "?"), "fake": fake,
            "before": (i.before or {}).get("quantity", 0), "after": (i.after or {}).get("quantity", 0),
            "notes_before": (i.before or {}).get("notes", ""), "notes_after": (i.after or {}).get("notes", ""),
        })
    cards = _card_info(per_card.keys() | {i.card_id for i in items if i.card_id})
    rows = [{"card": cards.get(cid, {"id": cid, "card_number": "?", "name": "?"}),
             "changes": sorted(ch, key=lambda c: (c["after"] - c["before"], c["location"]))}
            for cid, ch in per_card.items()]
    rows.sort(key=lambda r: r["card"].get("card_number", ""))
    return {**_summary(activity, items), "copies": rows, "other": _other_changes(items, names, cards)}


def _filtered(request):
    qs = Activity.objects.select_related("undo_of", "restore_point")
    p = request.query_params
    if p.get("kind"):
        qs = qs.filter(kind__in=p["kind"].split(","))
    if p.get("source"):
        qs = qs.filter(source=p["source"])
    if p.get("card"):
        number = Card.objects.filter(pk=p["card"]).values_list("card_number", flat=True).first()
        ids = Card.objects.filter(card_number=number).values_list("id", flat=True) if number else [p["card"]]
        qs = qs.filter(items__card_id__in=list(ids))
    if p.get("location"):
        qs = qs.filter(items__location_id=p["location"])
    if p.get("q"):
        q = p["q"].strip()
        cards = Card.objects.filter(Q(card_number__iexact=q) | Q(name__icontains=q)).values_list("id", flat=True)[:200]
        qs = qs.filter(Q(title__icontains=q) | Q(items__card_id__in=list(cards)))
    for name, lookup in (("from", "updated_at__date__gte"), ("to", "updated_at__date__lte")):
        if p.get(name):
            try:
                qs = qs.filter(**{lookup: datetime.strptime(p[name], "%Y-%m-%d").date()})
            except ValueError:
                pass
    return qs.distinct()


class HistoryView(APIView):
    """GET ?kind=&source=&card=&location=&q=&from=&to=&page=: las acciones, de la más reciente a la más antigua."""

    def get(self, request):
        qs = _filtered(request)
        try:
            page = max(1, int(request.query_params.get("page", 1)))
            size = min(100, max(1, int(request.query_params.get("page_size", PAGE_SIZE))))
        except ValueError:
            page, size = 1, PAGE_SIZE
        total = qs.count()
        acts = list(qs.order_by("-updated_at", "-id")[(page - 1) * size: page * size])
        items: dict[int, list] = {}
        for item in ActivityItem.objects.filter(activity__in=acts):
            items.setdefault(item.activity_id, []).append(item)
        return Response({
            "count": total, "page": page, "pages": max(1, -(-total // size)),
            "results": [_summary(a, items.get(a.id, [])) for a in acts],
            "kinds": recorder.KIND_LABELS,
        })


class HistoryDetailView(APIView):
    def get(self, request, pk):
        return Response(_detail(get_object_or_404(Activity.objects.select_related("undo_of"), pk=pk)))


def _short(a: Activity) -> dict:
    return {"id": a.id, "title": a.title, "updated_at": a.updated_at}


class HistoryUndoView(APIView):
    """GET: si se puede deshacer (y qué acciones posteriores lo impiden). POST: deshacerla."""

    def get(self, request, pk):
        activity = get_object_or_404(Activity, pk=pk)
        check = recorder.preview_undo(activity)
        return Response({"ok": check["ok"] and activity.undone_at is None, "undone": activity.undone_at is not None,
                         "conflict_rows": check["conflict_rows"], "later": [_short(a) for a in check["later"]],
                         "detail": _detail(activity)})

    def post(self, request, pk):
        activity = get_object_or_404(Activity, pk=pk)
        if activity.kind == "undo":  # rehacer lo deshecho llegará más adelante
            return Response({"detail": "This change can't be undone from here."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            done = recorder.undo(activity)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except recorder.UndoConflict as exc:
            return Response({"detail": "Some of these cards changed afterwards: undo those changes first.",
                             "conflict_rows": exc.rows, "later": [_short(a) for a in exc.later]},
                            status=status.HTTP_409_CONFLICT)
        return Response({"undone": activity.id, "activity": _summary(done, list(done.items.all())) if done else None})


class RestorePointsView(APIView):
    def get(self, request):
        return Response({"results": [
            {"id": p.id, "created_at": p.created_at, "reason": p.reason, "activity": p.activity_id}
            for p in RestorePoint.objects.only("id", "created_at", "reason", "activity_id")
        ], "days": recorder.RESTORE_POINT_DAYS})


class RestorePointRestoreView(APIView):
    """GET: qué cambiaría al volver a ese punto. POST: volver (queda como una acción más, que se puede deshacer)."""

    def get(self, request, pk):
        point = get_object_or_404(RestorePoint, pk=pk)
        changes = recorder.restore_point_changes(point)

        class Item:  # lo mismo que ActivityItem, para reutilizar el resumen
            def __init__(self, c):
                self.model, self.key, self.before, self.after = c["model"], c["key"], c["before"], c["after"]
                self.card_id, self.location_id = recorder._refs(self.model, self.key, self.after, self.before)

        items = [Item(c) for c in changes]
        per_card, added, removed = recorder.copy_moves(items)
        return Response({"id": point.id, "reason": point.reason, "created_at": point.created_at,
                         "changes": len(changes), "cards": len(per_card), "added": added, "removed": removed})

    def post(self, request, pk):
        point = get_object_or_404(RestorePoint, pk=pk)
        done = recorder.restore_to_point(point)
        return Response({"activity": _summary(done, list(done.items.all())) if done else None})
