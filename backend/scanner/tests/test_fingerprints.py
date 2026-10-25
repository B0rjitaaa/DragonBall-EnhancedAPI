import tempfile
from unittest import mock

from django.core.management import call_command
from django.test import TestCase, override_settings

from cards.models import Card
from collection.models import CollectionEntry, Location
from collection.services import delete_location
from scanner.fingerprints import build_pending
from scanner.models import CardFingerprint, Scan
from vision.preprocess import encode_jpeg

from .synthetic import make_card

BASE = "https://files.bandai-tcg-plus.com/card_image/DB-EN/BT1/"


def fake_image(url: str) -> bytes:
    """Imagen sintética distinta por URL (sin red)."""
    return encode_jpeg(make_card(sum(map(ord, url)) % 1000))


@mock.patch("scanner.fingerprints.get_image", side_effect=fake_image)
class FingerprintTests(TestCase):
    def setUp(self):
        self.leader = Card.objects.create(id=4, card_number="BT1-001", name="Champa", card_type="LEADER",
                                          image_url=BASE + "BT1-001.png", back_image_url=BASE + "BT1-001_b.png")
        self.battle = Card.objects.create(id=7, card_number="BT1-008", name="Vados", image_url=BASE + "BT1-008.png")

    def faces(self):
        return sorted(CardFingerprint.objects.values_list("card_id", "face"))

    def test_front_and_back_and_only_what_is_pending(self, get_image):
        self.assertEqual(build_pending(), (3, 0))
        self.assertEqual(self.faces(), [(4, "back"), (4, "front"), (7, "front")])
        self.assertEqual(build_pending(), (0, 0))  # nada pendiente
        Card.objects.filter(id=7).update(image_url=BASE + "BT1-008_v2.png")  # imagen cambiada en Bandai
        self.assertEqual(build_pending(), (1, 0))
        self.assertEqual(CardFingerprint.objects.get(card_id=7).source_url, BASE + "BT1-008_v2.png")

    def test_only_some_cards(self, get_image):
        self.assertEqual(build_pending(card_ids=[7]), (1, 0))
        self.assertEqual(self.faces(), [(7, "front")])

    def test_a_broken_image_does_not_stop_the_batch(self, get_image):
        get_image.side_effect = lambda url: b"no es una imagen" if "008" in url else fake_image(url)
        self.assertEqual(build_pending(), (2, 1))

    def test_add_printing_is_recognisable_right_away(self, get_image):
        call_command("add_printing", "7", "--image", "https://example.com/promo.jpg", "--set", "Event Pack",
                     "--id", "900000123", stdout=open("/dev/null", "w"))
        self.assertTrue(CardFingerprint.objects.filter(card_id=900000123, source_url="https://example.com/promo.jpg").exists())

    def test_sync_with_new_cards_queues_the_fingerprints(self, get_image):
        from cards import tasks

        with mock.patch.object(tasks, "BandaiClient") as client, \
                mock.patch("scanner.tasks.build_fingerprints.delay") as delay:
            client.return_value.list_card_ids.return_value = []
            client.return_value.fetch_details.return_value = ([], [])
            self.assertEqual(tasks.sync_cards()["status"], "success")
            delay.assert_not_called()  # sin cartas nuevas, nada que calcular
            client.return_value.list_card_ids.return_value = [55]
            client.return_value.fetch_details.side_effect = lambda ids, on_result: (on_result({
                "id": 55, "card_name": "Nueva", "card_number": "BT30-001", "card_config": [],
                "image_url": BASE + "BT30-001.png",
            }), ([], []))[1]
            self.assertEqual(tasks.sync_cards()["created"], 1)
            delay.assert_called_once()


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class DeleteLocationWithScansTests(TestCase):
    def test_scans_keep_pointing_at_their_copies(self):
        card = Card.objects.create(id=4, card_number="BT1-001", name="Champa")
        binder = Location.objects.create(name="Archivador", kind="binder")
        entry = CollectionEntry.objects.create(card=card, location=binder, quantity=1)
        scan = Scan.objects.create(matched_card=card, added_to_collection=True, collection_entry=entry, status="done")
        delete_location(binder)
        scan.refresh_from_db()
        self.assertEqual(scan.collection_entry.location, Location.default())
