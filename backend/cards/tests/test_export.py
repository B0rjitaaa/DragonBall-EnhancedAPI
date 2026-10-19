from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from cards.models import Card


class ExportTests(TestCase):
    def setUp(self):
        self.old = Card.objects.create(id=4, card_number="BT1-001", name="Champa", raw={"id": 4, "card_name": "Champa"})
        self.new = Card.objects.create(id=5, card_number="BT1-002", name="Vados", raw={"id": 5, "card_name": "Vados"})
        Card.objects.filter(pk=4).update(updated_at=timezone.now() - timedelta(days=3))
        self.client = APIClient()

    def test_full_export_returns_raw_bandai_records(self):
        data = self.client.get("/api/cards/export/").data
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["results"], [{"id": 4, "card_name": "Champa"}, {"id": 5, "card_name": "Vados"}])
        self.assertIn("generated_at", data)

    def test_incremental_export(self):
        since = (timezone.now() - timedelta(days=1)).isoformat()
        data = self.client.get("/api/cards/export/", {"updated_since": since}).data
        self.assertEqual([r["id"] for r in data["results"]], [5])

    def test_invalid_date(self):
        self.assertEqual(self.client.get("/api/cards/export/", {"updated_since": "ayer"}).status_code, 400)
