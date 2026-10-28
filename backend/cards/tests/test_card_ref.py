from django.test import TestCase
from rest_framework.test import APIClient

from cards.models import Card


class CardRefTests(TestCase):
    """Enlaces legibles a una carta: ?card=BT20-149 (primera impresión), BT20-149-2… (las siguientes)."""

    def setUp(self):
        for card_id in (54229, 54230, 54300):
            Card.objects.create(id=card_id, card_number="BT20-149", name="Android 21", rarity_code="SCR")
        Card.objects.create(id=10, card_number="P-331", name="Promo")
        self.client = APIClient()

    def ref(self, ref):
        return self.client.get(f"/api/cards/ref/{ref}/")

    def test_resolve(self):
        self.assertEqual(self.ref("BT20-149").json(), {"id": 54229, "ref": "BT20-149"})
        self.assertEqual(self.ref("bt20-149-2").json()["id"], 54230)
        self.assertEqual(self.ref("BT20-149-3").json()["id"], 54300)
        self.assertEqual(self.ref("54230").json()["ref"], "BT20-149-2")  # los enlaces viejos con id
        self.assertEqual(self.ref("P-331").json()["id"], 10)
        for missing in ("BT20-149-4", "BT20-149-1", "XX-1"):
            self.assertEqual(self.ref(missing).status_code, 404, missing)

    def test_detail_has_ref_and_prints(self):
        data = self.client.get("/api/cards/54230/").json()
        self.assertEqual(data["ref"], "BT20-149-2")
        self.assertEqual([p["ref"] for p in data["prints"]], ["BT20-149", "BT20-149-2", "BT20-149-3"])
        self.assertEqual(self.client.get("/api/cards/10/").json()["prints"], [])
