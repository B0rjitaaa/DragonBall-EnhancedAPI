import io

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from cards.importer import upsert_cards
from cards.models import Card
from cards.printings import CUSTOM_ID_START, add_printing

BASE = {
    "id": 5594,
    "card_number": "BT9-132",
    "card_name": "Cell's Earth-Destroying Kamehameha",
    "card_text": "[Activate:Battle] If your Leader Card is green…",
    "image_url": "https://files.bandai-tcg-plus.com/card_image/DB-EN/BT9/BT9-132.png",
    "card_set": "Universal Onslaught [DBS-B09]",
}
IMAGE = "https://tcgplayer-cdn.tcgplayer.com/product/266669_in_1000x1000.jpg"


class PrintingTests(TestCase):
    def setUp(self):
        upsert_cards([BASE])
        self.base = Card.objects.get(id=5594)

    def test_clones_the_card_with_its_own_image_and_set(self):
        card = add_printing(self.base, IMAGE, "Event Pack 09 (Alternate Foil)")
        self.assertEqual(card.id, CUSTOM_ID_START + 1)
        self.assertEqual((card.card_number, card.name, card.text), (self.base.card_number, self.base.name, self.base.text))
        self.assertEqual((card.image_url, card.card_set), (IMAGE, "Event Pack 09 (Alternate Foil)"))
        self.assertEqual(card.raw["custom_printing_of"], 5594)
        self.assertEqual(self.base.raw["image_url"], BASE["image_url"])  # la original no cambia
        self.assertEqual(add_printing(self.base, IMAGE, "Otra").id, CUSTOM_ID_START + 2)

    def test_reimporting_bandai_does_not_touch_custom_printings(self):
        card = add_printing(self.base, IMAGE, "Event Pack 09 (Alternate Foil)")
        upsert_cards([BASE])
        self.assertEqual(Card.objects.get(id=card.id).image_url, IMAGE)

    def test_custom_printing_is_exported_to_the_scanner(self):
        card = add_printing(self.base, IMAGE, "Event Pack 09 (Alternate Foil)")
        ids = [r["id"] for r in APIClient().get("/api/cards/export/").data["results"]]
        self.assertIn(card.id, ids)

    def test_command_and_id_validation(self):
        call_command("add_printing", "5594", image=IMAGE, card_set="EP09", card_id=CUSTOM_ID_START + 266669, stdout=io.StringIO())
        self.assertTrue(Card.objects.filter(id=CUSTOM_ID_START + 266669).exists())
        with self.assertRaises(ValueError):
            add_printing(self.base, IMAGE, "EP09", card_id=1234)
