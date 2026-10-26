import json
import re

from django.core.cache import cache
from django.db.models import Case, F, IntegerField, Q, QuerySet, Value, When
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from collection.models import Location
from collection.serializers import LocationSerializer
from collection.services import delete_location

from collection.models import CollectionEntry

from .collection import (
    CollectionUnavailable,
    Scope,
    adjust_owned,
    backup_document,
    fetch_export,
    move_owned,
    note_owned,
    reorder_owned,
)
from .facets import cached_facets
from .models import BanListEntry, Card, KeywordSkill, SyncRun
from .parsing import normalize_search
from .query import FIELDS, QueryError, fields_schema, params_to_tree, tree_to_q
from .serializers import (
    BanListEntrySerializer, CardDetailSerializer, KeywordSkillSerializer, CardListSerializer, SearchRequestSerializer,
    SyncRunSerializer,
)
from .tasks import sync_cards

NATURAL = ["series", "set_number", "collector_number", "card_number", "id"]
ORDERINGS = {
    "number": NATURAL,
    "name": ["name", *NATURAL],
    "energy": ["energy", *NATURAL],
    "power": ["power", *NATURAL],
    "newest": ["-id"],
}


def apply_ordering(qs: QuerySet, ordering: str | None) -> QuerySet:
    ordering = (ordering or "number").strip()
    desc = ordering.startswith("-")
    fields = ORDERINGS.get(ordering.lstrip("-"))
    if not fields:
        raise ValidationError({"ordering": f"Valores válidos: {', '.join(ORDERINGS)} (prefijo - para descendente)"})
    exprs = []
    for name in fields:
        field_desc = name.startswith("-") != desc
        expr = F(name.lstrip("-"))
        exprs.append(expr.desc(nulls_last=True) if field_desc else expr.asc(nulls_last=True))
    return qs.order_by(*exprs)


def text_search(q: str | None) -> Q:
    """Busca la frase en nombre, número y texto, ignorando corchetes y mayúsculas.

    'it gains Barrier' encuentra '... it gains [Barrier]'.
    """
    needle = normalize_search(q)
    if not needle:
        return Q()
    return Q(search_text__contains=needle)


def build_queryset(q: str | None, tree: dict | None, extra: dict | None = None) -> QuerySet:
    try:
        condition = tree_to_q(tree) & tree_to_q(extra)
    except QueryError as exc:
        raise ValidationError({"query": str(exc)}) from exc
    return Card.objects.filter(condition & text_search(q))


def parse_query_param(raw: str | None) -> dict | None:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValidationError({"query": f"JSON no válido: {exc}"}) from exc


class CardViewSet(viewsets.ReadOnlyModelViewSet):
    """Listado y detalle de cartas.

    GET  /api/cards/?color=Red&energy_max=3&keyword=Barrier&q=goku&ordering=-power
    POST /api/cards/search/ {"q": "...", "query": {árbol}, "ordering": "power", "page": 1}
    """

    def get_serializer_class(self):
        return CardDetailSerializer if self.action == "retrieve" else CardListSerializer

    def get_queryset(self):
        if self.action == "retrieve":
            return Card.objects.all()
        params = self.request.query_params
        qs = build_queryset(params.get("q"), parse_query_param(params.get("query")), params_to_tree(params))
        return apply_ordering(qs, params.get("ordering"))

    @extend_schema(
        parameters=[
            OpenApiParameter("q", str, description="Búsqueda libre"),
            OpenApiParameter("query", str, description="Árbol de condiciones en JSON"),
            OpenApiParameter("ordering", str, description="number, name, energy, power, newest (- = desc)"),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(parameters=[OpenApiParameter("updated_since", str, description="ISO 8601: solo cartas creadas o cambiadas desde entonces")])
    @action(detail=False)
    def export(self, request):
        """Registros originales de Bandai TCG+ (el mismo formato que cartas_dbs.json).

        Lo usa DragonBall-CameraCardChecker para mantener su catálogo al día sin
        hablar directamente con Bandai: GET /api/cards/export/?updated_since=…
        """
        qs = Card.objects.order_by("id")
        raw_since = request.query_params.get("updated_since")
        if raw_since:
            since = parse_datetime(raw_since)
            if since is None:
                raise ValidationError({"updated_since": "Fecha ISO 8601 no válida"})
            qs = qs.filter(updated_at__gte=since)
        return Response({
            "generated_at": timezone.now().isoformat(),
            "count": qs.count(),
            "results": list(qs.values_list("raw", flat=True)),
        })

    @extend_schema(request=SearchRequestSerializer, responses=CardListSerializer(many=True))
    @action(detail=False, methods=["post"])
    def search(self, request):
        body = SearchRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data
        scope = collection_scope(data.get("scope"), data.get("location"), data.get("fake"), data.get("include_fakes"))

        qs = build_queryset(data.get("q"), data.get("query"))
        ordering = (data.get("ordering") or "number").strip()
        if scope is not None:
            qs = qs.filter(id__in=scope.card_ids())
        if scope is not None and ordering.lstrip("-") == "quantity":
            # Por copias (solo en Mi colección); desempate por número de carta.
            natural = apply_ordering(qs, "number").query.order_by
            qs = scope.with_quantity(qs).order_by("-owned_qty" if ordering.startswith("-") else "owned_qty", *natural)
        elif scope is not None and ordering == "position" and scope.location_id is not None:
            # «Mi orden»: el que el usuario ha dado a las cartas de esa ubicación.
            natural = apply_ordering(qs, "number").query.order_by
            qs = scope.with_position(qs).order_by("owned_pos", *natural)
        else:
            qs = apply_ordering(qs, ordering)

        size, number = data["page_size"], data["page"]
        total = qs.count()
        items = CardListSerializer(qs[(number - 1) * size: number * size], many=True).data
        response = {
            "count": total,
            "page": number,
            "page_size": size,
            "pages": max(1, -(-total // size)),
            "results": items,
        }
        if scope is not None:
            details = scope.details([c["id"] for c in items])
            response["results"] = [{**c, **details.get(c["id"], {})} for c in items]
            response["total_copies"] = scope.total_copies(qs)
            # Las copias apuntan al catálogo (clave ajena): ya no puede haber cartas que falten.
            response["missing"] = []
        return Response(response)


class FieldsView(APIView):
    """Campos filtrables, su tipo y los operadores permitidos (para construir la UI)."""

    def get(self, request):
        return Response(fields_schema())


class FacetsView(APIView):
    """GET: valores y recuentos globales. POST {q, query}: recuentos dentro de la búsqueda actual."""

    def get(self, request):
        scope = collection_scope(
            request.query_params.get("scope"),
            request.query_params.get("location"),
            request.query_params.get("fake"),
            request.query_params.get("include_fakes"),
        )
        if scope is None:
            return Response(cached_facets(Card.objects.all()))
        # Ámbito Mi colección: la huella de sus copias en la clave de caché.
        return Response(cached_facets(Card.objects.filter(id__in=scope.card_ids()), {"owned": scope.fingerprint()}))

    def post(self, request):
        """Body: {q, query, only?: [campos], scope?: "collection"}. `only` limita el cálculo a esos campos."""
        q, tree = request.data.get("q"), request.data.get("query")
        only = request.data.get("only") or None
        if only is not None and (not isinstance(only, list) or any(k not in FIELDS for k in only)):
            raise ValidationError({"only": "Lista de campos no válida"})
        scope = collection_scope(
            request.data.get("scope"), request.data.get("location"), request.data.get("fake"),
            request.data.get("include_fakes"),
        )
        qs, payload = build_queryset(q, tree), {"q": q, "query": tree}
        if scope is not None:
            qs, payload["owned"] = qs.filter(id__in=scope.card_ids()), scope.fingerprint()
        return Response(cached_facets(qs, payload, only))


class KeywordSkillsView(APIView):
    """Keyword skills oficiales con su texto, las variantes que existen en las cartas
    ('Over Realm X' -> 'Over Realm 3', 'Over Realm 4'…) y un mapa alias -> nombre oficial
    para poner tooltips en el texto de las cartas."""

    def get(self, request):
        from django.core.cache import cache

        from .facets import _array_counts
        from .importer import FACETS_VERSION_KEY
        from .skills import DECK_RULES, Catalog

        key = f"keyword-skills:v{cache.get(FACETS_VERSION_KEY) or 0}"
        data = cache.get(key)
        if data is None:
            catalog = Catalog.from_db()
            rows = KeywordSkill.objects.all()
            variants: dict[str, list[dict]] = {}
            aliases: dict[str, str] = {}
            qs = Card.objects.all()
            for item in _array_counts(qs, "keywords"):
                name = catalog.official_name(item["value"])
                variants.setdefault(name, []).append(item)
                aliases[item["value"]] = name
            for item in _array_counts(qs, "keyword_mentions"):
                aliases.setdefault(item["value"], catalog.official_name(item["value"]))
            first = rows.first()
            data = {
                "updated": first.list_updated if first else "",
                "source": first.source if first else "",
                "skills": KeywordSkillSerializer(rows, many=True).data,
                "variants": {k: sorted(v, key=lambda x: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", x["value"])]) for k, v in variants.items() if len(v) > 1},
                "aliases": aliases,
                "deck_rules": DECK_RULES,
            }
            cache.set(key, data, 60 * 60 * 24)
        return Response(data)


class BanListView(APIView):
    """Lista oficial de cartas prohibidas y limitadas."""

    def get(self, request):
        entries = BanListEntry.objects.all()
        first = entries.first()
        return Response({
            "updated": first.list_updated if first else "",
            "source": first.source if first else "",
            "fetched_at": first.fetched_at if first else None,
            "entries": BanListEntrySerializer(entries, many=True).data,
        })


class SyncRunViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Historial de sincronizaciones con Bandai. Lanzar uno nuevo requiere ser staff."""

    queryset = SyncRun.objects.all()
    serializer_class = SyncRunSerializer

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    def create(self, request):
        full = str(request.data.get("full", "false")).lower() in {"1", "true", "yes"}
        result = sync_cards.delay(full=full)
        return Response({"task_id": result.id, "full": full}, status=status.HTTP_202_ACCEPTED)



def _bool(value, name: str) -> bool | None:
    """true/false (también "1"/"0" en la query string); None si no viene."""
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value
    if str(value).lower() in ("1", "true", "yes"):
        return True
    if str(value).lower() in ("0", "false", "no"):
        return False
    raise ValidationError({name: "Debe ser true o false"})


def collection_scope(request_scope: str | None, location=None, fake=None, include_fakes=None) -> Scope | None:
    """Mi colección si el ámbito es "collection" (o None).

    Por defecto solo cuentan las copias auténticas; `include_fakes=true` suma
    también las falsas y `fake=true` deja solo las falsas. `location` limita a
    una ubicación.
    """
    if request_scope != "collection":
        return None
    location_id = None
    if location not in (None, ""):
        try:
            location_id = int(location)
        except (TypeError, ValueError):
            raise ValidationError({"location": "Debe ser un id de ubicación"}) from None
    only_fakes = bool(_bool(fake, "fake"))
    return Scope(location_id, with_fakes=only_fakes or bool(_bool(include_fakes, "include_fakes")), only_fakes=only_fakes)


def collection_error(exc: CollectionUnavailable) -> Response:
    return Response({**exc.data, "detail": str(exc)}, status=exc.status)


class MyCollectionView(APIView):
    """Resumen de Mi colección: totales y cartas escaneadas que este catálogo aún no tiene."""

    def get(self, request):
        scope = Scope(with_fakes=True)
        cards = CardListSerializer(Card.objects.filter(id__in=scope.card_ids()), many=True).data
        details = scope.details([c["id"] for c in cards])
        return Response({
            "total_cards": len(cards),
            "total_copies": sum(d["quantity"] for d in details.values()),
            "missing": [],
            "results": [{**c, **details.get(c["id"], {})} for c in cards],
        })


def _int(value, name: str, required: bool = True) -> int | None:
    if value in (None, "") and not required:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError({name: "Debe ser un entero"}) from None


def _known_card(card_id: int) -> None:
    if not Card.objects.filter(id=card_id).exists():
        raise ValidationError({"card_id": "Carta desconocida"})


class MyCollectionAdjustView(APIView):
    """Botones − / + de Mi colección: POST {card_id, delta, location?} (delta entre -10 y 10, distinto de 0).

    Sin `location`, + suma a "Sin ubicar" y − quita de "Sin ubicar" (o de la única
    ubicación con copias); si están repartidas, 409 con el reparto para elegir.
    """

    def post(self, request):
        card_id, delta = _int(request.data.get("card_id"), "card_id"), _int(request.data.get("delta"), "delta")
        location = _int(request.data.get("location"), "location", required=False)
        fake = _bool(request.data.get("fake"), "fake")
        if delta == 0 or abs(delta) > 10:
            raise ValidationError({"delta": "Entre -10 y 10, distinto de 0"})
        _known_card(card_id)
        try:
            return Response({"card_id": card_id, **adjust_owned(card_id, delta, location, fake)})
        except CollectionUnavailable as exc:
            return collection_error(exc)


class MyCollectionMoveView(APIView):
    """Mover copias entre ubicaciones: POST {card_id, source, target, quantity, source_fake?, target_fake?}.

    Con source == target y target_fake distinto de source_fake, marca copias como falsas o auténticas.
    """

    def post(self, request):
        card_id = _int(request.data.get("card_id"), "card_id")
        source, target = _int(request.data.get("source"), "source"), _int(request.data.get("target"), "target")
        quantity = _int(request.data.get("quantity"), "quantity")
        if quantity < 1:
            raise ValidationError({"quantity": "Al menos 1"})
        _known_card(card_id)
        try:
            source_fake = bool(_bool(request.data.get("source_fake"), "source_fake"))
            target_fake = _bool(request.data.get("target_fake"), "target_fake")
            note_line = str(request.data.get("note_line") or "")[:200] or None
            return Response({"card_id": card_id, **move_owned(card_id, source, target, quantity, source_fake, target_fake, note_line)})
        except CollectionUnavailable as exc:
            return collection_error(exc)


class MyCollectionNoteView(APIView):
    """Nota de las copias de una carta en una ubicación: POST {card_id, location, notes, fake?}."""

    def post(self, request):
        card_id, location = _int(request.data.get("card_id"), "card_id"), _int(request.data.get("location"), "location")
        notes = str(request.data.get("notes") or "")[:500]
        _known_card(card_id)
        try:
            fake = bool(_bool(request.data.get("fake"), "fake"))
            return Response({"card_id": card_id, **note_owned(card_id, location, notes, fake)})
        except CollectionUnavailable as exc:
            return collection_error(exc)


class MyCollectionReorderView(APIView):
    """«Mi orden»: POST {location, card_ids: [en el orden deseado]} (arrastrar cartas en una ubicación)."""

    def post(self, request):
        location = _int(request.data.get("location"), "location")
        ids = request.data.get("card_ids")
        if not isinstance(ids, list) or not ids or len(ids) > 500:
            raise ValidationError({"card_ids": "Lista de ids de carta (1-500)"})
        card_ids = [_int(i, "card_ids") for i in ids]
        try:
            reorder_owned(location, card_ids)
        except CollectionUnavailable as exc:
            return collection_error(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)


LOCATION_FIELDS = ("name", "kind", "notes", "position")


def deck_leaders() -> dict[int, dict]:
    """Líder de cada mazo: su carta LEADER (las Z-Leader no se despiertan), con la imagen
    de su cara despertada. Si hubiera varias, la auténtica y con más copias."""
    best: dict[int, tuple] = {}
    rows = CollectionEntry.objects.filter(location__kind="deck", card__card_type="LEADER").values_list(
        "location_id", "card_id", "fake", "quantity"
    )
    for location_id, card_id, fake, quantity in rows:
        rank = (not fake, quantity, -card_id)
        if location_id not in best or rank > best[location_id][0]:
            best[location_id] = (rank, card_id)
    cards = Card.objects.only("id", "card_number", "name", "back_name", "image_url", "back_image_url").in_bulk(
        [card_id for _, card_id in best.values()]
    )
    return {
        location_id: {
            "id": card.id,
            "card_number": card.card_number,
            "name": card.back_name or card.name,
            "image": card.back_image_url or card.image_url,
            "awakened": bool(card.back_image_url),
        }
        for location_id, (_, card_id) in best.items()
        if (card := cards.get(card_id))
    }


class LocationsView(APIView):
    """Ubicaciones de Mi colección: GET lista con totales (y el líder de cada mazo), POST crea."""

    def get(self, request):
        locations = LocationSerializer.listing()
        leaders = deck_leaders() if any(loc["kind"] == "deck" for loc in locations) else {}
        return Response([{**loc, "leader": leaders.get(loc["id"])} for loc in locations])

    def post(self, request):
        body = LocationSerializer(data={k: request.data[k] for k in LOCATION_FIELDS if k in request.data})
        body.is_valid(raise_exception=True)
        return Response(LocationSerializer(body.save()).data, status=status.HTTP_201_CREATED)


class LocationDetailView(APIView):
    """PATCH renombra o cambia el tipo; DELETE la borra (sus copias vuelven a "Sin ubicar")."""

    def patch(self, request, pk: int):
        location = Location.objects.filter(pk=pk).first()
        if location is None:
            return Response({"detail": "Ubicación desconocida"}, status=status.HTTP_404_NOT_FOUND)
        body = LocationSerializer(location, data={k: request.data[k] for k in LOCATION_FIELDS if k in request.data},
                                  partial=True)
        body.is_valid(raise_exception=True)
        body.save()
        return Response(next(loc for loc in LocationSerializer.listing() if loc["id"] == pk))

    def delete(self, request, pk: int):
        location = Location.objects.filter(pk=pk).first()
        if location is None:
            return Response({"detail": "Ubicación desconocida"}, status=status.HTTP_404_NOT_FOUND)
        try:
            delete_location(location)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyCollectionBackupView(APIView):
    """Descarga la colección como JSON (botón "Descargar copia" de Mi colección)."""

    def get(self, request):
        entries, locations = fetch_export(), LocationSerializer.listing()
        now = timezone.localtime()
        doc = backup_document(entries, now.isoformat(timespec="seconds"), locations)
        # Una ubicación y una carta por línea: ocupa poco y se puede leer o comparar a simple vista.
        def block(items):
            return ",\n".join(json.dumps(i, ensure_ascii=False, separators=(",", ":")) for i in items)

        head = json.dumps({k: v for k, v in doc.items() if k not in ("locations", "cards")}, ensure_ascii=False)[:-1]
        body = f'{head},\n"locations": [\n{block(doc["locations"])}\n],\n"cards": [\n{block(doc["cards"])}\n]}}\n'
        response = HttpResponse(body, content_type="application/json; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="mi-coleccion-{now:%Y-%m-%d}.json"'
        return response
