import io
import tempfile
from unittest import mock

from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from cards import thumbs
from cards.models import Card


def png(width=600, height=838, mode="RGBA") -> bytes:
    buf = io.BytesIO()
    Image.new(mode, (width, height), (200, 30, 30, 255) if mode == "RGBA" else (200, 30, 30)).save(buf, "PNG")
    return buf.getvalue()


class ThumbTests(TestCase):
    def setUp(self):
        # Una carpeta por test: cada uno empieza sin miniaturas generadas.
        self.enterContext(override_settings(CARD_IMAGES_DIR=self.enterContext(tempfile.TemporaryDirectory())))
        self.card = Card.objects.create(id=4, card_number="BT1-001", name="Champa", image_url="https://x/BT1-001.png")
        self.client = APIClient()

    def test_search_results_carry_a_versioned_thumb_url(self):
        data = self.client.post("/api/cards/search/", {}, format="json").data["results"][0]
        self.assertEqual(data["thumb_url"], f"/api/thumbs/4/{thumbs.version('https://x/BT1-001.png')}.webp")
        self.assertEqual(data["image_url"], "https://x/BT1-001.png")  # la completa sigue ahí

    @mock.patch("scanner.images.get_image", return_value=png())
    def test_thumb_is_generated_once_small_and_cached_forever(self, get_image):
        url = thumbs.thumb_url(4, self.card.image_url)
        first = self.client.get(url)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first["Content-Type"], "image/webp")
        self.assertIn("immutable", first["Cache-Control"])
        image = Image.open(io.BytesIO(b"".join(first.streaming_content)))
        self.assertEqual((image.width, image.height), (320, 447))  # misma proporción
        self.client.get(url)
        get_image.assert_called_once()  # la segunda vez, del disco

    @mock.patch("scanner.images.get_image", return_value=png())
    def test_changed_image_redirects_to_its_new_thumb(self, get_image):
        old = thumbs.thumb_url(4, self.card.image_url)
        Card.objects.filter(id=4).update(image_url="https://x/BT1-001_v2.png")
        response = self.client.get(old)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], thumbs.thumb_url(4, "https://x/BT1-001_v2.png"))

    @mock.patch("scanner.images.get_image", side_effect=OSError("sin red"))
    def test_without_thumb_falls_back_to_the_original(self, get_image):
        response = self.client.get(thumbs.thumb_url(4, self.card.image_url))
        self.assertEqual((response.status_code, response["Location"]), (302, "https://x/BT1-001.png"))
        self.assertEqual(self.client.get("/api/thumbs/999/abc.webp").status_code, 404)
