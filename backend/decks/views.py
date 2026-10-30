from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from cards.models import Card
from collection.models import Location

from . import services
from .models import DeckVersion, Match, PickList
from .serializers import ListCardSerializer, MatchSerializer, SideSerializer, VersionSerializer


def _deck(pk) -> Location:
    return get_object_or_404(Location, pk=pk, kind=Location.Kind.DECK)


def _cards(listing: dict) -> list[dict]:
    return [
        {"bandai_id": card_id, "section": section, "quantity": n}
        for (card_id, section), n in sorted(listing.items(), key=lambda kv: (kv[0][1], kv[0][0]))
    ]


def _card_ids(payload) -> set[int]:
    """Ids de carta que aparecen en una respuesta (para añadir sus datos de catálogo)."""
    ids: set[int] = set()
    if isinstance(payload, dict):
        for key in ("bandai_id", "opponent_leader_bandai_id", "leader_bandai_id"):
            if isinstance(payload.get(key), int):
                ids.add(payload[key])
        for value in payload.values():
            ids |= _card_ids(value)
    elif isinstance(payload, list):
        for item in payload:
            ids |= _card_ids(item)
    return ids


def _with_catalog(payload: dict) -> dict:
    """Añade `catalog`: los datos de catálogo (imagen, nombre, tipo…) de las cartas de la respuesta."""
    from cards.serializers import CardListSerializer

    cards = Card.objects.filter(id__in=_card_ids(payload))
    return {**payload, "catalog": {c["id"]: c for c in CardListSerializer(cards, many=True).data}}


def _listing(data) -> dict[tuple[int, str], int]:
    """[{bandai_id, section, quantity}] → {(card_id, sección): copias}. Mazo / Z según el tipo de la carta."""
    rows = ListCardSerializer(data=data, many=True)
    rows.is_valid(raise_exception=True)
    cards = Card.objects.in_bulk([r["bandai_id"] for r in rows.validated_data])
    listing: dict[tuple[int, str], int] = {}
    for r in rows.validated_data:
        card = cards.get(r["bandai_id"])
        if card is None or not r["quantity"]:
            continue
        section = r["section"] if r["section"] == "side" else services.section_of(card)
        listing[(card.id, section)] = listing.get((card.id, section), 0) + r["quantity"]
    return listing


def _location(loc: Location) -> dict:
    return {"id": loc.id, "name": loc.name, "kind": loc.kind, "is_default": loc.is_default}


def _plan(deck: Location, listing: dict) -> dict:
    plan = services.restore_plan(deck, listing)
    return {
        "default_target": _location(Location.default()),
        "outgoing": [{"bandai_id": r["card_id"], "quantity": r["quantity"], "fakes": r["fakes"]}
                     for r in plan["outgoing"]],
        "incoming": [{
            "bandai_id": r["card_id"], "quantity": r["quantity"], "missing": r["missing"],
            "sources": [{**_location(s["location"]), "authentic": s["authentic"], "fakes": s["fakes"]}
                        for s in r["sources"]],
        } for r in plan["incoming"]],
    }


def _diff(old: dict, new: dict) -> list[dict]:
    rows = services.diff(old, new)
    return [{"bandai_id": r["card_id"], "section": r["section"], "delta": r["delta"]} for r in rows]


def _pick_summary(deck: Location) -> dict | None:
    picks = PickList.objects.filter(deck=deck).first()
    return {"total": picks.total, "done": len(picks.done)} if picks else None


class DeckPickListView(APIView):
    """La lista de recogida de un mazo importado: leerla, guardar las cartas ya sacadas y quitarla."""

    def _get(self, pk) -> PickList:
        return get_object_or_404(PickList, deck=_deck(pk))

    def _data(self, picks: PickList) -> dict:
        ids = {c["bandai_id"] for g in picks.groups for c in g.get("cards", [])}
        return _with_catalog({"deck": picks.deck.name, "groups": picks.groups, "done": picks.done,
                              "created_at": picks.created_at, "card_ids": [{"bandai_id": i} for i in ids]})

    def get(self, request, pk):
        return Response(self._data(self._get(pk)))

    def patch(self, request, pk):
        picks = self._get(pk)
        valid = {f"{g['location_id']}-{c['bandai_id']}" for g in picks.groups for c in g.get("cards", [])}
        picks.done = [k for k in dict.fromkeys(str(k) for k in request.data.get("done") or []) if k in valid]
        picks.save(update_fields=["done"])
        return Response(self._data(picks))

    def delete(self, request, pk):
        self._get(pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DeckView(APIView):
    """Un mazo: su lista actual, sus versiones (con su balance) y estadísticas por líder rival."""

    def get(self, request, pk):
        deck = _deck(pk)
        current = services.current_list(deck)
        versions = list(deck.deck_versions.prefetch_related("matches", "cards"))
        # La caja se compara con la lista principal (o, si aún no hay, con la última guardada).
        latest = next((v for v in versions if v.principal), versions[0] if versions else None)
        all_matches = [m for v in versions for m in v.matches.all()]
        return Response(_with_catalog({
            "deck": {"id": deck.id, "name": deck.name},
            "current": _cards(current),
            "principal": next((v.id for v in versions if v.principal), None),
            # Lo que hay en la caja frente a la lista principal (o la última guardada).
            "compared_to": latest.number if latest else None,
            "changes": _diff(services.version_list(latest), current) if latest else [],
            "versions": [
                {**VersionSerializer(v).data, "record": services.record(v.matches.all()),
                 "copies": sum(c.quantity for c in v.cards.all())}
                for v in versions
            ],
            "matches": [
                {**MatchSerializer(m).data, "version_number": number}
                for number, m in sorted(
                    ((v.number, m) for v in versions for m in v.matches.all()),
                    key=lambda vm: (vm[1].played_on, vm[1].created_at), reverse=True,
                )
            ],
            "record": services.record(all_matches),
            "by_leader": services.by_leader(all_matches),
            "pick_list": _pick_summary(deck),
        }))


class DeckVersionsView(APIView):
    """POST {name?, notes?, cards?}: guarda una lista nueva.

    `cards` ([{bandai_id, section, quantity}]): la lista editada; sin ella, lo que hay en la caja.
    Si coincide con lo que hay en la caja, pasa a ser la principal.
    """

    def post(self, request, pk):
        deck = _deck(pk)
        body = VersionSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        listing = _listing(request.data["cards"]) if isinstance(request.data.get("cards"), list) else None
        version = services.save_version(
            deck, body.validated_data.get("name", ""), body.validated_data.get("notes", ""), listing=listing
        )
        return Response(VersionSerializer(version).data, status=status.HTTP_201_CREATED)


class DeckPlanView(APIView):
    """POST {cards}: qué copias habría que mover para que la caja del mazo tenga esa lista."""

    def post(self, request, pk):
        deck = _deck(pk)
        cards = request.data.get("cards") if isinstance(request.data, dict) else None
        return Response(_with_catalog(_plan(deck, _listing(cards if isinstance(cards, list) else []))))


class VersionDetailView(APIView):
    """GET: cartas de la versión, cambios respecto a la anterior y sus partidas. PATCH: nombre/notas."""

    def get(self, request, pk):
        version = get_object_or_404(DeckVersion.objects.prefetch_related("cards", "matches"), pk=pk)
        previous = version.deck.deck_versions.filter(number__lt=version.number).order_by("-number").first()
        listing = services.version_list(version)
        matches = list(version.matches.all())
        return Response(_with_catalog({
            **VersionSerializer(version).data,
            "deck": version.deck_id,
            "cards": _cards(listing),
            "previous": previous.number if previous else None,
            "changes": _diff(services.version_list(previous), listing) if previous else [],
            "matches": MatchSerializer(matches, many=True).data,
            "record": services.record(matches),
            "by_leader": services.by_leader(matches),
        }))

    def patch(self, request, pk):
        version = get_object_or_404(DeckVersion, pk=pk)
        body = VersionSerializer(version, data=request.data, partial=True)
        body.is_valid(raise_exception=True)
        body.save()
        return Response(body.data)

    def delete(self, request, pk):
        version = get_object_or_404(DeckVersion, pk=pk)
        if version.matches.exists():
            return Response({"detail": "This version has recorded matches: delete them first."}, status=400)
        version.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class VersionRestoreView(APIView):
    """Hacer principal una versión (las copias se mueven físicamente).

    GET: el plan (qué sale del mazo, qué entra y de dónde, qué falta).
    POST {default_target?, targets?: {bandai_id: ubicación}, sources?: {bandai_id: ubicación}}: lo ejecuta.
    """

    def get(self, request, pk):
        version = get_object_or_404(DeckVersion, pk=pk)
        return Response(_with_catalog({"version": version.number, **_plan(version.deck, services.version_list(version))}))

    def post(self, request, pk):
        version = get_object_or_404(DeckVersion, pk=pk)
        body = request.data if isinstance(request.data, dict) else {}

        def location(value):
            return get_object_or_404(Location, pk=int(value))

        def by_card(mapping):
            if not isinstance(mapping, dict):
                return {}
            known = set(Card.objects.filter(id__in=[int(k) for k in mapping]).values_list("id", flat=True))
            return {int(k): location(v) for k, v in mapping.items() if int(k) in known and v}

        default_target = location(body["default_target"]) if body.get("default_target") else Location.default()
        try:
            result = services.restore_version(
                version, default_target, by_card(body.get("targets")), by_card(body.get("sources"))
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response({**result, "missing": [{"bandai_id": k, "quantity": n} for k, n in result["missing"].items()]})


class DeckMatchesView(APIView):
    """POST: anota una partida. Sin `version`, con la lista actual (si cambió, se guarda una versión nueva)."""

    def post(self, request, pk):
        deck = _deck(pk)
        body = MatchSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        version = body.validated_data.get("version")
        if version is not None and version.deck_id != deck.id:
            return Response({"version": "Not a version of this deck"}, status=400)
        match = body.save(version=version or services.version_for_match(deck))
        return Response(MatchSerializer(match).data, status=status.HTTP_201_CREATED)


class MatchDetailView(APIView):
    def patch(self, request, pk):
        match = get_object_or_404(Match, pk=pk)
        body = MatchSerializer(match, data=request.data, partial=True)
        body.is_valid(raise_exception=True)
        body.save()
        return Response(body.data)

    def delete(self, request, pk):
        get_object_or_404(Match, pk=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DeckSideView(APIView):
    """POST {bandai_id, quantity}: cuántas copias de esa carta del mazo van al side deck."""

    def post(self, request, pk):
        deck = _deck(pk)
        body = SideSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        card = get_object_or_404(Card, id=body.validated_data["bandai_id"])
        n = services.set_side(deck, card, body.validated_data["quantity"])
        return Response({"bandai_id": card.id, "side": n})


class DeckToHistoryView(APIView):
    """GET: qué copias saldrían del mazo. POST: lo pasa al histórico y sus copias van a «Sin ubicar»."""

    def get(self, request, pk):
        deck = _deck(pk)
        return Response({"deck": deck.name, "cards": services.history_preview(deck)})

    def post(self, request, pk):
        deck = _deck(pk)
        if deck.status == Location.Status.PARKED:
            return Response({"detail": "The deck is already archived"}, status=status.HTTP_400_BAD_REQUEST)
        moved = services.move_to_history(deck)
        return Response({"deck": deck.name, "target": Location.default().name, "cards": moved})


class DeckBackInUseView(APIView):
    """POST: un mazo del histórico vuelve a usarse (y se trae una copia de su líder)."""

    def post(self, request, pk):
        deck = _deck(pk)
        if deck.status != Location.Status.PARKED:
            return Response({"detail": "The deck is already in use"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"deck": deck.name, "leader": services.back_in_use(deck)})


class DeckImportPreviewView(APIView):
    """Importar un mazo (enlace de DeckPlanet / Top Deck Diffusion / Time Chamber o lista en texto): qué tienes."""

    def post(self, request):
        from .importer import DeckImportError, parse_source, parsed_from_lines, preview

        try:
            # Con `lines` (otra vez, al elegir el mazo destino) no se vuelve a descargar la página.
            if request.data.get("lines"):
                deck = parsed_from_lines(request.data["lines"], str(request.data.get("source") or "text"),
                                         str(request.data.get("name") or ""))
            else:
                deck = parse_source(str(request.data.get("source") or ""))
            data = preview(deck, request.data.get("target"))
        except DeckImportError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(_with_catalog(data))


class DeckImportView(APIView):
    """Crea el mazo importado (o, con `target`, guarda la lista como versión nueva de ese mazo): `lines` (de la
    vista previa), `name` y `take_from` (mazos de los que coger copias)."""

    def post(self, request):
        from .importer import DeckImportError, create_deck, parsed_from_lines

        take_from = {int(d) for d in request.data.get("take_from") or [] if str(d).isdigit()}
        try:
            deck = parsed_from_lines(request.data.get("lines"), str(request.data.get("source") or "text"))
            result = create_deck(deck, str(request.data.get("name") or ""), take_from, request.data.get("target"))
        except DeckImportError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(_with_catalog(result), status=status.HTTP_201_CREATED)
