import io
import json
from unittest import mock
from urllib.error import HTTPError, URLError

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from cards.collection import CACHE_KEY
from cards.models import Card

UNPLACED = {"location_id": 1, "location": "Sin ubicar", "location_kind": "other", "notes": ""}
DECK = {"location_id": 2, "location": "Mazo rojo", "location_kind": "deck", "notes": ""}
ENTRIES = [
    {"bandai_id": 4, "card_number": "BT1-001", "name": "Champa", "quantity": 2, **UNPLACED},
    {"bandai_id": 4, "card_number": "BT1-001", "name": "Champa", "quantity": 1, **DECK, "notes": "titular"},
    {"bandai_id": 1088, "card_number": "BT1-005", "name": "Champa PR", "quantity": 1, **UNPLACED},
    {"bandai_id": 999999, "card_number": "BT32-001", "name": "Nueva", "quantity": 1, **UNPLACED},
]


def _response(payload):
    body = io.BytesIO(json.dumps(payload).encode())
    body.__enter__ = lambda self=body: self
    body.__exit__ = lambda *a: None
    return body


@override_settings(CARD_CHECKER_URL="http://checker")
class MyCollectionTests(TestCase):
    """Mi colección = el buscador con scope=collection."""

    def setUp(self):
        cache.delete(CACHE_KEY)
        Card.objects.create(id=4, card_number="BT1-001", name="Champa", card_type="LEADER", colors=["Red"])
        Card.objects.create(id=1088, card_number="BT1-005", name="Champa PR", card_type="BATTLE", colors=["Red"])
        Card.objects.create(id=7, card_number="BT1-008", name="Vados", card_type="BATTLE", colors=["Blue"])
        self.client = APIClient()
        patcher = mock.patch("cards.collection.urlopen", side_effect=lambda *a, **k: _response(ENTRIES))
        self.urlopen = patcher.start()
        self.addCleanup(patcher.stop)

    def search(self, **body):
        return self.client.post("/api/cards/search/", body, format="json")

    def test_search_in_collection_only_returns_owned_cards_with_copies(self):
        data = self.search(scope="collection").data
        self.assertEqual(self.urlopen.call_args.args[0], "http://checker/api/collection/export/")
        self.assertEqual(sorted(r["card_number"] for r in data["results"]), ["BT1-001", "BT1-005"])
        champa = next(r for r in data["results"] if r["id"] == 4)
        self.assertEqual(champa["quantity"], 3)
        self.assertEqual(
            [(loc["name"], loc["quantity"], loc["notes"]) for loc in champa["locations"]],
            [("Sin ubicar", 2, ""), ("Mazo rojo", 1, "titular")],
        )
        self.assertEqual(data["total_copies"], 4)
        self.assertEqual(data["missing"], ["BT32-001"])  # escaneada, pero no está en este catálogo

    def test_filters_apply_inside_the_collection(self):
        query = {"op": "and", "children": [{"field": "type", "operator": "in", "value": ["LEADER"]}]}
        data = self.search(scope="collection", query=query).data
        self.assertEqual([r["card_number"] for r in data["results"]], ["BT1-001"])
        self.assertEqual(data["total_copies"], 3)

    def test_location_filter_shows_the_copies_there(self):
        data = self.search(scope="collection", location=2).data
        self.assertEqual([(r["card_number"], r["quantity"]) for r in data["results"]], [("BT1-001", 1)])
        self.assertEqual(data["total_copies"], 1)
        self.assertEqual(data["results"][0]["total_quantity"], 3)
        facets = self.client.get("/api/facets/?scope=collection&location=2").data
        self.assertEqual(facets["total"], 1)

    def test_facets_only_count_owned_cards(self):
        facets = self.client.get("/api/facets/?scope=collection").data
        self.assertEqual(facets["total"], 2)
        colors = {v["value"]: v["count"] for v in facets["facets"]["color"]["values"]}
        self.assertEqual(colors, {"Red": 2})  # Vados (Blue) no la tienes
        battle = {"op": "and", "children": [{"field": "type", "operator": "in", "value": ["BATTLE"]}]}
        post = self.client.post("/api/facets/", {"scope": "collection", "query": battle}, format="json").data
        self.assertEqual(post["total"], 1)

    def test_order_by_quantity(self):
        data = self.search(scope="collection", ordering="-quantity").data
        self.assertEqual([r["card_number"] for r in data["results"]], ["BT1-001", "BT1-005"])
        data = self.search(scope="collection", ordering="quantity").data
        self.assertEqual([r["card_number"] for r in data["results"]], ["BT1-005", "BT1-001"])

    def test_normal_search_does_not_touch_the_checker(self):
        data = self.search().data
        self.assertEqual(data["count"], 3)
        self.assertNotIn("total_copies", data)
        self.urlopen.assert_not_called()

    def test_summary_endpoint(self):
        data = self.client.get("/api/my-collection/").data
        self.assertEqual((data["total_cards"], data["total_copies"]), (2, 4))
        self.assertEqual(data["missing"], ["BT32-001"])

    def test_backup_downloads_every_entry_as_compact_json(self):
        response = self.client.get("/api/my-collection/backup/")
        self.assertEqual(response.status_code, 200)
        self.assertRegex(response["Content-Disposition"], r'attachment; filename="mi-coleccion-\d{4}-\d{2}-\d{2}\.json"')
        doc = json.loads(response.content)
        self.assertEqual((doc["format"], doc["version"]), ("dbs-collection", 2))
        self.assertEqual((doc["total_cards"], doc["total_copies"]), (3, 5))  # incluye las que no están en el catálogo
        self.assertEqual(doc["cards"][:2], [
            {"id": 4, "number": "BT1-001", "name": "Champa", "qty": 1, "location": "Mazo rojo", "notes": "titular"},
            {"id": 4, "number": "BT1-001", "name": "Champa", "qty": 2, "location": "Sin ubicar"},
        ])
        self.assertEqual(len(response.content.decode().splitlines()), len(doc["cards"]) + 2)  # una carta por línea

    def test_backup_with_checker_down(self):
        self.urlopen.side_effect = URLError("connection refused")
        self.assertEqual(self.client.get("/api/my-collection/backup/").status_code, 502)

    def test_checker_down_returns_502(self):
        self.urlopen.side_effect = URLError("connection refused")
        self.assertEqual(self.search(scope="collection").status_code, 502)
        self.assertEqual(self.client.get("/api/facets/?scope=collection").status_code, 502)

    @override_settings(CARD_CHECKER_URL="")
    def test_not_configured_returns_503(self):
        self.assertEqual(self.search(scope="collection").status_code, 503)


    def test_adjust_forwards_to_the_checker_and_drops_the_cache(self):
        self.search(scope="collection")  # llena la caché
        calls = []

        def fake(req, *a, **k):
            if hasattr(req, "data") and req.data:
                calls.append((req.full_url, json.loads(req.data)))
                return _response({"bandai_id": 4, "quantity": 4, "locations": [{"id": 1, "name": "Sin ubicar", "quantity": 4}]})
            return _response(ENTRIES)

        self.urlopen.side_effect = fake
        data = self.client.post("/api/my-collection/adjust/", {"card_id": 4, "delta": 1}, format="json").data
        self.assertEqual(calls, [("http://checker/api/collection/adjust/", {"bandai_id": 4, "delta": 1})])
        self.assertEqual((data["card_id"], data["quantity"]), (4, 4))
        self.assertIsNone(cache.get(CACHE_KEY))  # la siguiente búsqueda relee la colección

    def test_adjust_validation(self):
        post = lambda body: self.client.post("/api/my-collection/adjust/", body, format="json")  # noqa: E731
        self.assertEqual(post({"card_id": 4, "delta": 0}).status_code, 400)
        self.assertEqual(post({"card_id": 4, "delta": 50}).status_code, 400)
        self.assertEqual(post({"card_id": 123456, "delta": 1}).status_code, 400)

    def test_adjust_with_checker_down(self):
        self.urlopen.side_effect = URLError("connection refused")
        response = self.client.post("/api/my-collection/adjust/", {"card_id": 4, "delta": -1}, format="json")
        self.assertEqual(response.status_code, 502)

    def _checker(self, responses):
        """urlopen falso: (método, ruta) -> respuesta o excepción; registra lo enviado."""
        sent = []

        def fake(req, *a, **k):
            if isinstance(req, str):
                return _response(ENTRIES)
            path = req.full_url.removeprefix("http://checker")
            sent.append((req.get_method(), path, json.loads(req.data) if req.data else None))
            result = responses[(req.get_method(), path)]
            if isinstance(result, Exception):
                raise result
            return _response(result)

        self.urlopen.side_effect = fake
        return sent

    def test_remove_with_copies_in_several_locations_returns_409_with_them(self):
        split = {"detail": "indica de cuál", "bandai_id": 4, "quantity": 3, "locations": [{"id": 2, "quantity": 2}, {"id": 3, "quantity": 1}]}
        error = HTTPError("http://checker/api/collection/adjust/", 409, "Conflict", {}, io.BytesIO(json.dumps(split).encode()))
        self._checker({("POST", "/api/collection/adjust/"): error})
        response = self.client.post("/api/my-collection/adjust/", {"card_id": 4, "delta": -1}, format="json")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["locations"], split["locations"])

    def test_move_and_note_are_forwarded(self):
        summary = {"bandai_id": 4, "quantity": 3, "locations": [{"id": 2, "name": "Mazo rojo", "quantity": 3}]}
        sent = self._checker({("POST", "/api/collection/move/"): summary, ("POST", "/api/collection/note/"): summary})
        data = self.client.post("/api/my-collection/move/", {"card_id": 4, "source": 1, "target": 2, "quantity": 2}, format="json").data
        self.assertEqual(data["locations"], summary["locations"])
        self.client.post("/api/my-collection/note/", {"card_id": 4, "location": 2, "notes": "pág. 3"}, format="json")
        self.assertEqual(sent, [
            ("POST", "/api/collection/move/", {"bandai_id": 4, "source": 1, "target": 2, "quantity": 2}),
            ("POST", "/api/collection/note/", {"bandai_id": 4, "location": 2, "notes": "pág. 3"}),
        ])

    def test_locations_are_managed_in_the_checker(self):
        listing = [{"id": 1, "name": "Sin ubicar", "is_default": True, "copies": 4}]
        sent = self._checker({
            ("GET", "/api/locations/"): listing,
            ("POST", "/api/locations/"): {"id": 2, "name": "Mazo rojo"},
            ("PATCH", "/api/locations/2/"): {"id": 2, "name": "Mazo azul"},
            ("DELETE", "/api/locations/2/"): None,
        })
        self.assertEqual(self.client.get("/api/my-collection/locations/").data, listing)
        self.assertEqual(self.client.post("/api/my-collection/locations/", {"name": "Mazo rojo", "kind": "deck", "x": 1}, format="json").status_code, 201)
        self.client.patch("/api/my-collection/locations/2/", {"name": "Mazo azul"}, format="json")
        self.assertEqual(self.client.delete("/api/my-collection/locations/2/").status_code, 204)
        self.assertEqual([m for m, *_ in sent], ["GET", "POST", "PATCH", "DELETE"])
        self.assertEqual(sent[1][2], {"name": "Mazo rojo", "kind": "deck"})  # solo los campos permitidos
