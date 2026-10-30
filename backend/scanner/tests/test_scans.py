import shutil
import tempfile
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from cards.models import Card
from scanner.models import CardFingerprint, Scan
from vision import fingerprint as fp
from vision.preprocess import encode_jpeg

from .synthetic import make_card, make_photo

MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA, CELERY_TASK_ALWAYS_EAGER=True)
class ScanApiTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.client = APIClient()
        self.cards = []
        for seed in range(10):
            card = Card.objects.create(
                id=seed + 1, card_number=f"BT1-{seed:03d}", name=f"Carta {seed}"
            )
            prints = fp.compute(make_card(seed))
            CardFingerprint.objects.create(
                card=card,
                source_url=f"https://example.com/{seed}.png",
                phash=prints.phash,
                dhash=prints.dhash,
                orb=prints.orb,
                orb_count=prints.orb_count,
            )
            self.cards.append(card)

    def test_upload_scan_identifies_card(self):
        upload = SimpleUploadedFile(
            "foto.jpg", encode_jpeg(make_photo(make_card(4))), content_type="image/jpeg"
        )
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post("/api/scanner/scans/", {"image": upload}, format="multipart")
        self.assertEqual(response.status_code, 202)

        detail = self.client.get(f"/api/scanner/scans/{response.data['id']}/").data
        self.assertEqual(detail["status"], Scan.Status.DONE)
        self.assertEqual(detail["matched_card"]["card_number"], "BT1-004")
        self.assertFalse(detail["needs_review"])
        self.assertTrue(detail["cropped_image"])
        self.assertEqual(detail["candidates"][0]["card_number"], "BT1-004")

    def _upload(self, card_seed):
        upload = SimpleUploadedFile(
            "foto.jpg", encode_jpeg(make_photo(make_card(card_seed))), content_type="image/jpeg"
        )
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post("/api/scanner/scans/", {"image": upload}, format="multipart")
        return self.client.get(f"/api/scanner/scans/{response.data['id']}/").data

    def test_confirm_learns_uncatalogued_printing(self):
        # Seed 99: "impresión" que no está en el catálogo (p. ej. una promo).
        first = self._upload(99)
        self.assertTrue(first["needs_review"])

        target = self.cards[3]
        response = self.client.post(
            f"/api/scanner/scans/{first['id']}/confirm/", {"card_id": target.id}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["confirmed"])
        self.assertFalse(response.data["needs_review"])
        self.assertEqual(response.data["matched_card"]["id"], target.id)
        self.assertTrue(CardFingerprint.objects.filter(card=target, face="scan").exists())

        # La siguiente foto de esa misma impresión ya se reconoce sola.
        second = self._upload(99)
        self.assertEqual(second["matched_card"]["id"], target.id)
        self.assertFalse(second["needs_review"])

    def test_confirm_rejects_unfinished_scan(self):
        scan = Scan.objects.create(source=Scan.Source.CAMERA)
        response = self.client.post(
            f"/api/scanner/scans/{scan.id}/confirm/", {"card_id": self.cards[0].id}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    @override_settings(CAMERA_URL="")
    def test_camera_scan_without_camera_fails_gracefully(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post("/api/scanner/scans/", {}, format="json")
        scan = Scan.objects.get(pk=response.data["id"])
        self.assertEqual(scan.source, Scan.Source.CAMERA)
        self.assertEqual(scan.status, Scan.Status.FAILED)
        self.assertIn("CAMERA_URL", scan.error)

    @override_settings(CAMERA_URL="http://camera:8080")
    def test_camera_scan_fails_when_camera_has_no_frames(self):
        with mock.patch("scanner.camera.requests.get") as get:
            get.return_value.status_code = 503
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post("/api/scanner/scans/", {}, format="json")
        scan = Scan.objects.get(pk=response.data["id"])
        self.assertEqual(scan.status, Scan.Status.FAILED)
        self.assertIn("webcam unplugged", scan.error)

    @override_settings(CAMERA_URL="http://camera:8080")
    def test_camera_preview_proxies_frame(self):
        with mock.patch("scanner.camera.requests.get") as get:
            get.return_value.status_code = 200
            get.return_value.ok = True
            get.return_value.content = b"\xff\xd8jpeg"
            response = self.client.get("/api/scanner/camera/preview/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")


class ImageCacheTests(TestCase):
    def test_local_path_mirrors_cdn(self):
        from scanner.images import local_path

        with override_settings(CARD_IMAGES_DIR="/cache"):
            path = local_path("https://files.bandai-tcg-plus.com/card_image/DB-EN/BT1/BT1-001_b.png")
        self.assertEqual(str(path), "/cache/DB-EN/BT1/BT1-001_b.png")

    def test_get_image_prefers_cache(self):
        from scanner.images import get_image

        with tempfile.TemporaryDirectory() as tmp, override_settings(CARD_IMAGES_DIR=tmp):
            url = "https://files.bandai-tcg-plus.com/card_image/DB-EN/BT1/BT1-001.png"
            with mock.patch("scanner.images._session") as session:
                session.return_value.get.return_value.content = b"png"
                self.assertEqual(get_image(url), b"png")
                self.assertEqual(get_image(url), b"png")
            self.assertEqual(session.return_value.get.call_count, 1)


class KeepWarmTests(TestCase):
    @override_settings(CAMERA_URL="")
    def test_keep_warm_runs_without_camera(self):
        from scanner.tasks import keep_warm

        keep_warm()  # no debe fallar aunque no haya cámara ni catálogo

    def test_keep_warm_is_scheduled(self):
        from django.conf import settings

        entry = settings.CELERY_BEAT_SCHEDULE["scanner-keep-warm"]
        self.assertEqual(entry["task"], "scanner.tasks.keep_warm")



class BurstFixture:
    """Catálogo sintético, una sesión y ayudantes para los tests de modo ráfaga."""

    def setUp(self):
        from collection.models import CollectionEntry

        self.Entry = CollectionEntry
        self.client = APIClient()
        self.cards = []
        for seed in range(10):
            card = Card.objects.create(
                id=seed + 1, card_number=f"BT1-{seed:03d}", name=f"Carta {seed}"
            )
            prints = fp.compute(make_card(seed))
            CardFingerprint.objects.create(
                card=card,
                source_url=f"https://example.com/{seed}.png",
                phash=prints.phash,
                dhash=prints.dhash,
                orb=prints.orb,
                orb_count=prints.orb_count,
            )
            self.cards.append(card)
        self.session = self.client.post("/api/scanner/sessions/", {}, format="json").data["id"]

    def _scan(self, image_bytes, after_empty=True):
        upload = SimpleUploadedFile("frame.jpg", image_bytes, content_type="image/jpeg")
        data = {"image": upload, "session": self.session, "after_empty": "true" if after_empty else "false"}
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post("/api/scanner/scans/", data, format="multipart")
        self.assertEqual(response.status_code, 202)
        return self.client.get(f"/api/scanner/scans/{response.data['id']}/").data

    def _card_photo(self, seed):
        return encode_jpeg(make_photo(make_card(seed)))

    def _quantity(self, card):
        entry = self.Entry.objects.filter(card=card).first()
        return entry.quantity if entry else 0

    def _stats(self):
        return self.client.get(f"/api/scanner/sessions/{self.session}/").data["stats"]



@override_settings(MEDIA_ROOT=MEDIA, CELERY_TASK_ALWAYS_EAGER=True, AUTO_ADD_MIN_CONFIDENCE=0.72)
class BurstModeTests(BurstFixture, TestCase):
    """Modo ráfaga: auto-añadido a la colección por encima del umbral."""

    def test_confident_scan_is_added_and_repeats_sum(self):
        first = self._scan(self._card_photo(4))
        self.assertTrue(first["added_to_collection"])
        self.assertGreaterEqual(first["confidence"], 0.72)
        self.assertEqual(self._quantity(self.cards[4]), 1)
        self._scan(self._card_photo(4))  # segunda copia
        self.assertEqual(self._quantity(self.cards[4]), 2)
        self.assertEqual(self._stats()["added"], 2)

    def test_uncatalogued_goes_to_review_and_confirm_adds_it(self):
        scan = self._scan(self._card_photo(99))
        self.assertFalse(scan["added_to_collection"])
        self.assertEqual(self._stats()["review"], 1)

        target = self.cards[3]
        confirmed = self.client.post(
            f"/api/scanner/scans/{scan['id']}/confirm/", {"card_id": target.id}, format="json"
        ).data
        self.assertTrue(confirmed["added_to_collection"])
        self.assertEqual(self._quantity(target), 1)
        self.assertEqual(self._stats()["review"], 0)

    def test_undo_removes_the_copy(self):
        self._scan(self._card_photo(4))
        second = self._scan(self._card_photo(4))
        response = self.client.post(f"/api/scanner/scans/{second['id']}/undo/", {}, format="json")
        self.assertTrue(response.data["dismissed"])
        self.assertFalse(response.data["added_to_collection"])
        self.assertEqual(self._quantity(self.cards[4]), 1)
        first_id = self.client.get(f"/api/scanner/sessions/{self.session}/").data["scans"][-1]["id"]
        self.client.post(f"/api/scanner/scans/{first_id}/undo/", {}, format="json")
        self.assertEqual(self._quantity(self.cards[4]), 0)  # la entrada se borra

    def test_changing_the_copies_of_an_added_scan(self):
        scan = self._scan(self._card_photo(4))
        url = f"/api/scanner/scans/{scan['id']}/copies/"
        self.assertEqual(self.client.post(url, {"copies": 3}, format="json").data["copies"], 3)
        self.assertEqual(self._quantity(self.cards[4]), 3)
        self.client.post(url, {"copies": 2}, format="json")
        self.assertEqual(self._quantity(self.cards[4]), 2)
        self.assertEqual(self.client.post(url, {"copies": 0}, format="json").status_code, 400)
        # Corregir la carta mueve todas sus copias; deshacer las quita todas.
        self.client.post(f"/api/scanner/scans/{scan['id']}/confirm/", {"card_id": self.cards[6].id}, format="json")
        self.assertEqual(self._quantity(self.cards[4]), 0)
        self.assertEqual(self._quantity(self.cards[6]), 2)
        self.client.post(f"/api/scanner/scans/{scan['id']}/undo/", {}, format="json")
        self.assertEqual(self._quantity(self.cards[6]), 0)
        self.assertEqual(self.client.post(url, {"copies": 2}, format="json").status_code, 400)

    def test_correcting_an_added_scan_moves_the_copy(self):
        scan = self._scan(self._card_photo(4))
        self.client.post(f"/api/scanner/scans/{scan['id']}/confirm/", {"card_id": self.cards[6].id}, format="json")
        self.assertEqual(self._quantity(self.cards[4]), 0)
        self.assertEqual(self._quantity(self.cards[6]), 1)

    def test_empty_frame_is_dismissed_silently(self):
        import numpy as np

        empty = np.full((720, 1280, 3), 35, np.uint8)
        scan = self._scan(encode_jpeg(empty))
        self.assertTrue(scan["dismissed"])
        self.assertFalse(scan["added_to_collection"])
        session = self.client.get(f"/api/scanner/sessions/{self.session}/").data
        self.assertEqual(session["stats"]["total"], 0)
        self.assertEqual(session["scans"], [])

    @override_settings(AUTO_ADD_MIN_CONFIDENCE=1.01)
    def test_threshold_is_respected(self):
        scan = self._scan(self._card_photo(4))
        self.assertFalse(scan["added_to_collection"])
        self.assertEqual(self._quantity(self.cards[4]), 0)

    def test_scans_outside_a_session_are_never_added(self):
        upload = SimpleUploadedFile("f.jpg", self._card_photo(4), content_type="image/jpeg")
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post("/api/scanner/scans/", {"image": upload}, format="multipart")
        self.assertEqual(self._quantity(self.cards[4]), 0)



@override_settings(MEDIA_ROOT=MEDIA, CELERY_TASK_ALWAYS_EAGER=True, AUTO_ADD_MIN_CONFIDENCE=0.65)
class RepeatGuardTests(BurstFixture, TestCase):
    """Misma carta dos veces seguidas sin vaciar la zona → "¿Otra copia?"."""

    def test_recolocated_card_is_not_added(self):
        self._scan(self._card_photo(4))
        repeat = self._scan(self._card_photo(4), after_empty=False)
        self.assertTrue(repeat["repeat_suspect"])
        self.assertFalse(repeat["added_to_collection"])
        self.assertEqual(self._quantity(self.cards[4]), 1)
        self.assertEqual(self._stats()["review"], 1)

    def test_confirming_the_repeat_adds_another_copy(self):
        self._scan(self._card_photo(4))
        repeat = self._scan(self._card_photo(4), after_empty=False)
        data = self.client.post(
            f"/api/scanner/scans/{repeat['id']}/confirm/", {"card_id": self.cards[4].id}, format="json"
        ).data
        self.assertTrue(data["added_to_collection"])
        self.assertFalse(data["repeat_suspect"])
        self.assertEqual(self._quantity(self.cards[4]), 2)

    def test_two_copies_with_empty_zone_between_are_added(self):
        self._scan(self._card_photo(4))
        self._scan(self._card_photo(4), after_empty=True)
        self.assertEqual(self._quantity(self.cards[4]), 2)

    def test_swapping_for_a_different_card_is_added(self):
        self._scan(self._card_photo(4))
        other = self._scan(self._card_photo(6), after_empty=False)
        self.assertTrue(other["added_to_collection"])
        self.assertFalse(other["repeat_suspect"])

    def test_confirming_the_repeat_with_several_copies(self):
        self._scan(self._card_photo(4))
        repeat = self._scan(self._card_photo(4), after_empty=False)
        data = self.client.post(
            f"/api/scanner/scans/{repeat['id']}/confirm/", {"card_id": self.cards[4].id, "copies": 3}, format="json"
        ).data
        self.assertEqual(data["copies"], 3)
        self.assertEqual(self._quantity(self.cards[4]), 4)
        self.assertEqual(self._stats()["copies"], 4)
        self.client.post(f"/api/scanner/scans/{repeat['id']}/undo/", {}, format="json")
        self.assertEqual(self._quantity(self.cards[4]), 1)

    def test_previous_undone_does_not_block(self):
        first = self._scan(self._card_photo(4))
        self.client.post(f"/api/scanner/scans/{first['id']}/undo/", {}, format="json")
        again = self._scan(self._card_photo(4), after_empty=False)
        self.assertTrue(again["added_to_collection"])



@override_settings(MEDIA_ROOT=MEDIA, CELERY_TASK_ALWAYS_EAGER=True, AUTO_ADD_MIN_CONFIDENCE=0.65)
class BinderSessionTests(BurstFixture, TestCase):
    """Sesión de archivador: carta a carta por casillas, con la posición en la nota."""

    def setUp(self):
        super().setUp()
        from collection.models import Location

        self.binder = Location.objects.create(name="Archivador rojo", kind="binder")
        self.session = self.client.post(
            "/api/scanner/sessions/", {"mode": "binder", "location": self.binder.id}, format="json"
        ).data["id"]

    def _slot(self, seed, page, slot):
        upload = SimpleUploadedFile("frame.jpg", self._card_photo(seed), content_type="image/jpeg")
        data = {"image": upload, "session": self.session, "after_empty": "true", "binder_page": page, "binder_slot": slot}
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post("/api/scanner/scans/", data, format="multipart")
        self.assertEqual(response.status_code, 202, response.data)
        return self.client.get(f"/api/scanner/scans/{response.data['id']}/").data

    def entry(self, card):
        return self.Entry.objects.get(card=card, location=self.binder)

    def test_cards_go_to_the_binder_with_their_position(self):
        scan = self._slot(4, page=12, slot=6)
        self.assertTrue(scan["added_to_collection"])
        self.assertEqual((scan["binder_page"], scan["binder_slot"]), (12, 6))
        self.assertEqual(self.entry(self.cards[4]).notes, "P. 12 · row 2 · col 3")
        session = self.client.get(f"/api/scanner/sessions/{self.session}/").data
        self.assertEqual(session["mode"], "binder")

    def test_same_card_side_by_side_is_two_copies(self):
        # En un archivador es normal tener copias juntas: no hay "¿Otra copia?".
        self._slot(4, page=1, slot=1)
        second = self._slot(4, page=1, slot=2)
        self.assertFalse(second["repeat_suspect"])
        entry = self.entry(self.cards[4])
        self.assertEqual(entry.quantity, 2)
        self.assertEqual(entry.notes.splitlines(), ["P. 1 · row 1 · col 1", "P. 1 · row 1 · col 2"])
        self.client.post(f"/api/scanner/scans/{second['id']}/undo/", {}, format="json")
        self.assertEqual((self.entry(self.cards[4]).quantity, self.entry(self.cards[4]).notes), (1, "P. 1 · row 1 · col 1"))

    def test_recapturing_a_slot_replaces_the_previous_card(self):
        first = self._slot(4, page=3, slot=5)
        self._slot(6, page=3, slot=5)
        self.assertTrue(self.client.get(f"/api/scanner/scans/{first['id']}/").data["dismissed"])
        self.assertFalse(self.Entry.objects.filter(card=self.cards[4]).exists())
        self.assertEqual(self.entry(self.cards[6]).notes, "P. 3 · row 2 · col 2")

    def test_webcam_capture_is_cropped_to_the_guide(self):
        import cv2
        import numpy as np

        from vision.preprocess import decode_image

        # Fotograma de la webcam: la carta a la derecha y otra carta a la izquierda.
        frame = np.full((720, 1280, 3), 40, np.uint8)
        frame[53:667, 760:1200] = cv2.resize(make_card(4), (440, 614))
        frame[53:667, 60:500] = cv2.resize(make_card(6), (440, 614))
        region = {"x": 0.57, "y": 0.03, "w": 0.4, "h": 0.94}
        body = {"session": self.session, "binder_page": 1, "binder_slot": 1, "region": region}
        with mock.patch("scanner.tasks.camera.get_frame", return_value=encode_jpeg(frame)), \
                self.captureOnCommitCallbacks(execute=True):
            response = self.client.post("/api/scanner/scans/", body, format="json")
        scan = self.client.get(f"/api/scanner/scans/{response.data['id']}/").data
        self.assertEqual(scan["matched_card"]["id"], self.cards[4].id)
        from scanner.models import Scan

        with Scan.objects.get(pk=scan["id"]).image.open("rb") as fh:
            height, width = decode_image(fh.read()).shape[:2]
            self.assertEqual((round(height / 10), width), (68, 512))  # solo el recorte
        bad = dict(body, region={"x": 0.9, "y": 0, "w": 0.5, "h": 1})
        self.assertEqual(self.client.post("/api/scanner/scans/", bad, format="json").status_code, 400)

    def test_slot_validation(self):
        upload = SimpleUploadedFile("frame.jpg", self._card_photo(4), content_type="image/jpeg")
        data = {"image": upload, "session": self.session, "binder_page": 1, "binder_slot": 10}
        self.assertEqual(self.client.post("/api/scanner/scans/", data, format="multipart").status_code, 400)

    def test_session_takes_the_size_of_the_binder(self):
        from collection.models import Location

        big = Location.objects.create(name="Archivador 4x4", kind="binder", binder_rows=4, binder_cols=4)
        # Lo que mande el navegador no cuenta: manda el archivador.
        body = {"mode": "binder", "location": big.id, "binder_rows": 2, "binder_cols": 2}
        session = self.client.post("/api/scanner/sessions/", body, format="json").data
        self.assertEqual((session["binder_rows"], session["binder_cols"]), (4, 4))
        self.session, self.binder = session["id"], big
        scan = self._slot(4, page=2, slot=16)
        self.assertTrue(scan["added_to_collection"])
        self.assertEqual(self.entry(self.cards[4]).notes, "P. 2 · row 4 · col 4")
        upload = SimpleUploadedFile("frame.jpg", self._card_photo(4), content_type="image/jpeg")
        data = {"image": upload, "session": self.session, "binder_page": 1, "binder_slot": 17}
        self.assertEqual(self.client.post("/api/scanner/scans/", data, format="multipart").status_code, 400)

    def test_size_chosen_for_a_destination_that_is_not_a_binder(self):
        body = {"mode": "binder", "binder_rows": 2, "binder_cols": 2}
        session = self.client.post("/api/scanner/sessions/", body, format="json").data
        self.assertEqual((session["binder_rows"], session["binder_cols"]), (2, 2))
        too_big = {"mode": "binder", "binder_rows": 7, "binder_cols": 2}
        self.assertEqual(self.client.post("/api/scanner/sessions/", too_big, format="json").status_code, 400)


@override_settings(MEDIA_ROOT=MEDIA)
class SessionLocationTests(TestCase):
    def test_burst_session_adds_into_its_location(self):
        from scanner.models import Scan, ScanSession
        from scanner.services import add_scan_to_collection

        from collection.models import CollectionEntry, Location

        self.Entry, self.Location = CollectionEntry, Location
        self.client = APIClient()
        self.card = Card.objects.create(id=4, card_number="BT1-001", name="Champa")
        deck = self.Location.objects.create(name="Mazo rojo")
        session = self.client.post("/api/scanner/sessions/", {"location": deck.id}, format="json").data
        self.assertEqual(session["location_name"], "Mazo rojo")
        scan = Scan.objects.create(session=ScanSession.objects.get(pk=session["id"]), matched_card=self.card, status="done")
        add_scan_to_collection(scan)
        self.assertEqual(list(self.Entry.objects.values_list("location__name", "quantity")), [("Mazo rojo", 1)])


def _stamped(card):
    """La misma carta con un sello (como una promo Judge): solo cambia una esquina."""
    import cv2

    stamped = card.copy()
    cv2.circle(stamped, (60, 380), 34, (255, 255, 255), -1)
    cv2.putText(stamped, "J", (46, 395), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 200), 3)
    return stamped


def _png(img):
    import cv2

    return cv2.imencode(".png", img)[1].tobytes()


@override_settings(MEDIA_ROOT=MEDIA, CELERY_TASK_ALWAYS_EAGER=True, AUTO_ADD_MIN_CONFIDENCE=0.65)
class SiblingPrintingTests(BurstFixture, TestCase):
    """Impresiones hermanas (mismo número, otra edición): se desempata por sus diferencias y,
    si no se puede, va a "Revisar" sin auto-añadirse."""

    def _add_promo(self, image):
        base = self.cards[4]
        promo = Card.objects.create(id=900_000_004, card_number=base.card_number, name=base.name,
                                    card_set="Judge Pack", image_url="https://example.com/promo.png")
        base.image_url = "https://example.com/4.png"
        base.save(update_fields=["image_url"])
        prints = fp.compute(image)
        CardFingerprint.objects.create(card=promo, source_url=promo.image_url, phash=prints.phash,
                                       dhash=prints.dhash, orb=prints.orb, orb_count=prints.orb_count)
        return base, promo

    def _images(self, base_img, promo_img):
        urls = {"https://example.com/4.png": _png(base_img), "https://example.com/promo.png": _png(promo_img)}
        return mock.patch("scanner.services.get_image", side_effect=lambda url: urls[url])

    def setUp(self):
        super().setUp()
        from scanner import services

        services._REFERENCES.clear()

    def test_stamped_promo_is_recognized_and_auto_added(self):
        stamped = _stamped(make_card(4))
        base, promo = self._add_promo(stamped)
        with self._images(make_card(4), stamped):
            scan = self._scan(encode_jpeg(make_photo(stamped)))
        self.assertEqual(scan["candidates"][0]["card_id"], promo.id)
        self.assertFalse(scan["needs_review"])
        self.assertTrue(scan["added_to_collection"])
        self.assertEqual((self._quantity(promo), self._quantity(base)), (1, 0))

    def test_plain_card_is_not_taken_for_the_promo(self):
        stamped = _stamped(make_card(4))
        base, promo = self._add_promo(stamped)
        with self._images(make_card(4), stamped):
            scan = self._scan(self._card_photo(4))
        self.assertEqual(scan["candidates"][0]["card_id"], base.id)
        self.assertEqual((self._quantity(base), self._quantity(promo)), (1, 0))

    def test_identical_editions_go_to_review_and_are_not_auto_added(self):
        base, promo = self._add_promo(make_card(4))
        with self._images(make_card(4), make_card(4)):
            scan = self._scan(self._card_photo(4))
        self.assertEqual(scan["candidates"][0]["card_number"], scan["candidates"][1]["card_number"])
        self.assertIn("card_set", scan["candidates"][0])
        self.assertTrue(scan["needs_review"])
        self.assertFalse(scan["added_to_collection"])
        self.assertEqual(self._quantity(base) + self._quantity(promo), 0)


@override_settings(MEDIA_ROOT=MEDIA, SCAN_RETENTION_HOURS=24, SCAN_PHOTOS_MAX_MB=2, SCAN_PHOTOS_TARGET_MB=1)
class CleanupScanPhotosTests(TestCase):
    """Fotos de los escaneos: se borran al pasar un día o, si ocupan demasiado, las más antiguas."""

    def scan(self, hours_ago, kb):
        from datetime import timedelta

        from django.core.files.base import ContentFile
        from django.utils import timezone

        scan = Scan.objects.create()
        scan.image.save(f"s{scan.pk}.jpg", ContentFile(b"x" * kb * 1024), save=False)
        scan.cropped_image.save(f"c{scan.pk}.jpg", ContentFile(b"y"), save=False)
        scan.save()
        Scan.objects.filter(pk=scan.pk).update(created_at=timezone.now() - timedelta(hours=hours_ago))
        return scan

    def with_photo(self):
        return sorted(Scan.objects.exclude(image="").values_list("pk", flat=True))

    def test_older_than_a_day(self):
        from scanner.tasks import cleanup_old_scans

        old, new = self.scan(25, 10), self.scan(2, 10)
        path = old.image.path
        self.assertEqual(cleanup_old_scans(), 1)
        self.assertEqual(self.with_photo(), [new.pk])
        self.assertTrue(Scan.objects.filter(pk=old.pk).exists())  # el registro se conserva
        import os

        self.assertFalse(os.path.exists(path))

    def test_over_the_size_limit_keeps_the_newest_up_to_the_target(self):
        from scanner.tasks import cleanup_old_scans

        scans = [self.scan(hours, 600) for hours in (5, 4, 3, 2)]  # 2,4 MB > 2 MB
        self.assertEqual(cleanup_old_scans(), 3)  # en 1 MB solo cabe la más reciente
        self.assertEqual(self.with_photo(), [scans[-1].pk])

    def test_under_the_limit_keeps_all_recent(self):
        from scanner.tasks import cleanup_old_scans

        self.scan(30, 1500)  # vieja y grande: no cuenta para el límite
        recent = [self.scan(h, 600) for h in (3, 2)]
        self.assertEqual(cleanup_old_scans(), 1)
        self.assertEqual(self.with_photo(), [s.pk for s in recent])
