from datetime import timedelta
from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from cards.models import BanListEntry, CardErrata, CardRuling, SyncRun

LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
BOTH_WORKERS = [{"celery@mint": {"ok": "pong"}}, {"scanner@mint": {"ok": "pong"}}]


@override_settings(CACHES=LOCMEM, CAMERA_URL="")
class HealthTests(TestCase):
    def setUp(self):
        cache.clear()
        now = timezone.now()
        SyncRun.objects.create(status=SyncRun.Status.SUCCESS, finished_at=now)
        BanListEntry.objects.create(card_number="BT1-001", status="banned")
        CardErrata.objects.all().delete()
        CardRuling.objects.all().delete()
        CardErrata.objects.create(card_number="BT1-001", after="x")
        CardRuling.objects.create(card_number="BT1-001", order=1, question="q", answer="a")
        self.client = APIClient()

    def get(self, workers=BOTH_WORKERS):
        with mock.patch("config.celery.app.control.ping", return_value=workers):
            return self.client.get("/api/health/")

    def checks(self, response):
        return {c["key"]: c for c in response.json()["checks"]}

    def test_all_ok(self):
        r = self.get()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")
        self.assertIsNone(self.checks(r)["camera"]["ok"])  # no configurada: no cuenta

    def test_scanner_worker_down_is_critical(self):
        r = self.get(workers=[{"celery@mint": {"ok": "pong"}}])
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()["status"], "down")
        self.assertFalse(self.checks(r)["scanner_worker"]["ok"])
        self.assertTrue(self.checks(r)["worker"]["ok"])

    def test_broker_unreachable_marks_workers_down(self):
        with mock.patch("config.celery.app.control.ping", side_effect=OSError("sin broker")):
            r = self.client.get("/api/health/")
        self.assertEqual(r.status_code, 503)
        self.assertIn("sin broker", self.checks(r)["worker"]["detail"])

    def test_stale_or_failed_sync_is_a_warning(self):
        SyncRun.objects.update(finished_at=timezone.now() - timedelta(days=3))
        r = self.get()
        self.assertEqual((r.status_code, r.json()["status"]), (200, "degraded"))
        self.assertFalse(self.checks(r)["cards_sync"]["ok"])

        SyncRun.objects.update(finished_at=timezone.now())
        SyncRun.objects.create(status=SyncRun.Status.FAILED, error="403 de Bandai")
        r = self.get()
        self.assertIn("403 de Bandai", self.checks(r)["cards_sync"]["detail"])

    def test_old_official_lists(self):
        CardErrata.objects.update(fetched_at=timezone.now() - timedelta(days=10))
        r = self.get()
        self.assertEqual(r.json()["status"], "degraded")
        self.assertFalse(self.checks(r)["errata"]["ok"])

    @override_settings(CAMERA_URL="http://camera:8080")
    def test_camera_without_webcam_is_reported_but_does_not_count(self):
        with mock.patch("cards.health.requests.get", return_value=mock.Mock(ok=False)):
            r = self.get()
        self.assertEqual(r.json()["status"], "ok")
        self.assertFalse(self.checks(r)["camera"]["ok"])
        self.assertIn("sin webcam", self.checks(r)["camera"]["detail"])
