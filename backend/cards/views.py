import json

from django.db.models import F, Q, QuerySet
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .facets import cached_facets
from .models import BanListEntry, Card, SyncRun
from .parsing import normalize_search
from .query import FIELDS, QueryError, fields_schema, params_to_tree, tree_to_q
from .serializers import (
    BanListEntrySerializer, CardDetailSerializer, CardListSerializer, SearchRequestSerializer,
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

    @extend_schema(request=SearchRequestSerializer, responses=CardListSerializer(many=True))
    @action(detail=False, methods=["post"])
    def search(self, request):
        body = SearchRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data
        qs = apply_ordering(build_queryset(data.get("q"), data.get("query")), data.get("ordering"))

        size, number = data["page_size"], data["page"]
        total = qs.count()
        items = qs[(number - 1) * size: number * size]
        return Response({
            "count": total,
            "page": number,
            "page_size": size,
            "pages": max(1, -(-total // size)),
            "results": CardListSerializer(items, many=True).data,
        })


class FieldsView(APIView):
    """Campos filtrables, su tipo y los operadores permitidos (para construir la UI)."""

    def get(self, request):
        return Response(fields_schema())


class FacetsView(APIView):
    """GET: valores y recuentos globales. POST {q, query}: recuentos dentro de la búsqueda actual."""

    def get(self, request):
        return Response(cached_facets(Card.objects.all()))

    def post(self, request):
        """Body: {q, query, only?: [campos]}. `only` limita el cálculo a esos campos."""
        q, tree = request.data.get("q"), request.data.get("query")
        only = request.data.get("only") or None
        if only is not None and (not isinstance(only, list) or any(k not in FIELDS for k in only)):
            raise ValidationError({"only": "Lista de campos no válida"})
        return Response(cached_facets(build_queryset(q, tree), {"q": q, "query": tree}, only))


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
