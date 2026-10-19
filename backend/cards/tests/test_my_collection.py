import io
import json
from unittest import mock
from urllib.error import URLError

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from cards.models import Card


def _response(payload):
    body = io.BytesIO(json.dumps(payload).encode())
    body.__enter__ = lambda self=body: self
    body.__exit__ = lambda *a: None
    return body


@override_settings(CARD_CHECKER_URL="http://checker")
class MyCollectionTests(TestCase):
    def setUp(self):
        Card.objects.create(id=4, card_number="BT1-001", name="Champa")
        Card.objects.create(id=1088, card_number="BT1-005", name="Champa PR")
        self.client = APIClient()

    def _get(self, entries):
        with mock.patch("cards.views.urlopen", return_value=_response(entries)) as urlopen:
            response = self.client.get("/api/my-collection/")
        return response, urlopen

    def test_joins_by_bandai_id_and_sums_conditions(self):
        response, urlopen = self._get(
            [
                {"bandai_id": 4, "card_number": "BT1-001", "name": "Champa", "quantity": 2, "condition": "near_mint"},
                {"bandai_id": 4, "card_number": "BT1-001", "name": "Champa", "quantity": 1, "condition": "played"},
                {"bandai_id": 1088, "card_number": "BT1-005", "name": "Champa PR", "quantity": 1, "condition": "near_mint"},
            ]
        )
        self.assertEqual(urlopen.call_args.args[0], "http://checker/api/collection/export/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_cards"], 2)
        self.assertEqual(response.data["total_copies"], 4)
        champa = next(r for r in response.data["results"] if r["id"] == 4)
        self.assertEqual(champa["quantity"], 3)
        self.assertEqual(champa["conditions"], {"near_mint": 2, "played": 1})
        self.assertEqual(champa["card_number"], "BT1-001")  # ficha de este catálogo

    def test_reports_cards_missing_from_this_catalog(self):
        response, _ = self._get(
            [{"bandai_id": 999999, "card_number": "BT32-001", "name": "Nueva", "quantity": 1, "condition": "near_mint"}]
        )
        self.assertEqual(response.data["missing"], ["BT32-001"])
        self.assertEqual(response.data["results"], [])

    def test_checker_down_returns_502(self):
        with mock.patch("cards.views.urlopen", side_effect=URLError("connection refused")):
            response = self.client.get("/api/my-collection/")
        self.assertEqual(response.status_code, 502)

    @override_settings(CARD_CHECKER_URL="")
    def test_not_configured_returns_503(self):
        self.assertEqual(self.client.get("/api/my-collection/").status_code, 503)
