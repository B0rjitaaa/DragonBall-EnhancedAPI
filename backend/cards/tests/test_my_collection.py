import io
import json
from unittest import mock
from urllib.error import URLError

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from cards.collection import CACHE_KEY
from cards.models import Card

ENTRIES = [
    {"bandai_id": 4, "card_number": "BT1-001", "name": "Champa", "quantity": 2, "condition": "near_mint"},
    {"bandai_id": 4, "card_number": "BT1-001", "name": "Champa", "quantity": 1, "condition": "played"},
    {"bandai_id": 1088, "card_number": "BT1-005", "name": "Champa PR", "quantity": 1, "condition": "near_mint"},
    {"bandai_id": 999999, "card_number": "BT32-001", "name": "Nueva", "quantity": 1, "condition": "near_mint"},
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
        self.assertEqual(champa["conditions"], {"near_mint": 2, "played": 1})
        self.assertEqual(data["total_copies"], 4)
        self.assertEqual(data["missing"], ["BT32-001"])  # escaneada, pero no está en este catálogo

    def test_filters_apply_inside_the_collection(self):
        query = {"op": "and", "children": [{"field": "type", "operator": "in", "value": ["LEADER"]}]}
        data = self.search(scope="collection", query=query).data
        self.assertEqual([r["card_number"] for r in data["results"]], ["BT1-001"])
        self.assertEqual(data["total_copies"], 3)

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

    def test_checker_down_returns_502(self):
        self.urlopen.side_effect = URLError("connection refused")
        self.assertEqual(self.search(scope="collection").status_code, 502)
        self.assertEqual(self.client.get("/api/facets/?scope=collection").status_code, 502)

    @override_settings(CARD_CHECKER_URL="")
    def test_not_configured_returns_503(self):
        self.assertEqual(self.search(scope="collection").status_code, 503)
