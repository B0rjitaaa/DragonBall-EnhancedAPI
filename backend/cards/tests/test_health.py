import json
import os
import tempfile
from datetime import timedelta
from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from cards.models import BanListEntry, CardErrata, CardRuling, SyncRun

LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
BOTH_WORKERS = [{"celery@mint": {"ok": "pong"}}, {"scanner@mint": {"ok": "pong"}}]


class HealthFixture:
    """Todo en orden (sync reciente, listas oficiales cargadas) y ayudantes para pedir /api/health/."""

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


@override_settings(CACHES=LOCMEM, CAMERA_URL="")
class HealthTests(HealthFixture, TestCase):

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


@override_settings(CACHES=LOCMEM, CAMERA_URL="")
class BackupHealthTests(HealthFixture, TestCase):
    """La copia de seguridad diaria, según el last_status.json que deja scripts/backup.sh."""

    def write(self, **fields):
        status = {"status": "ok", "finished_at": timezone.now().isoformat(), "size": "1,5G", "remote": "ok",
                  "message": "copia completa", **fields}
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as fh:
            json.dump(status, fh)
        self.addCleanup(os.remove, path)
        return override_settings(BACKUP_STATUS_FILE=path)

    def backup(self):
        r = self.get()
        return r.json()["status"], self.checks(r)["backup"]

    def test_not_configured_does_not_count(self):
        status, check = self.backup()
        self.assertEqual(status, "ok")
        self.assertIsNone(check["ok"])

    def test_recent_and_replicated(self):
        with self.write():
            status, check = self.backup()
        self.assertEqual(status, "ok")
        self.assertTrue(check["ok"])
        self.assertIn("replicada a la Raspberry", check["detail"])

    def test_failed_old_or_not_replicated_is_a_warning(self):
        cases = [
            ({"status": "error", "message": "falló en: volumen media"}, "falló"),
            ({"finished_at": (timezone.now() - timedelta(hours=40)).isoformat()}, "hace"),
            ({"remote": "error"}, "réplica a la Raspberry falló"),
        ]
        for fields, text in cases:
            with self.subTest(fields=fields), self.write(**fields):
                status, check = self.backup()
                self.assertEqual(status, "degraded")
                self.assertFalse(check["ok"])
                self.assertIn(text, check["detail"])

    def test_missing_file(self):
        with override_settings(BACKUP_STATUS_FILE="/no/existe/last_status.json"):
            status, check = self.backup()
        self.assertEqual(status, "degraded")
        self.assertIn("no hay registro", check["detail"])


@override_settings(CACHES=LOCMEM, CAMERA_URL="", TELEGRAM_BOT_TOKEN="t", TELEGRAM_CHAT_ID="1")
class AlertTests(HealthFixture, TestCase):
    """Avisos por Telegram: una vez al fallar (los críticos tras 10 min) y otra al arreglarse."""

    def run_check(self, workers=BOTH_WORKERS):
        from cards import alerts

        with mock.patch("config.celery.app.control.ping", return_value=workers), \
                mock.patch("cards.alerts.requests.post", return_value=mock.Mock(ok=True)) as post:
            sent = alerts.check_and_alert()
        return sent, [c.kwargs["data"] for c in post.call_args_list]

    def age_state(self, key, minutes):
        from cards import alerts

        state = cache.get(alerts.STATE_KEY)
        state[key]["since"] = (timezone.now() - timedelta(minutes=minutes)).isoformat()
        cache.set(alerts.STATE_KEY, state, None)

    def test_all_ok_sends_nothing(self):
        self.assertEqual(self.run_check(), ([], []))

    def test_critical_waits_ten_minutes_then_alerts_once_and_on_recovery(self):
        only_celery = [{"celery@mint": {"ok": "pong"}}]
        self.assertEqual(self.run_check(only_celery)[0], [])  # recién caído: aún no

        self.age_state("scanner_worker", 11)
        sent, calls = self.run_check(only_celery)
        self.assertEqual(len(sent), 1)
        self.assertIn("Worker del escáner", sent[0])
        self.assertIn("desde hace 11 min", sent[0])
        self.assertFalse(calls[0]["disable_notification"])  # crítico: con sonido

        self.assertEqual(self.run_check(only_celery)[0], [])  # ya avisado: no se repite

        sent, _ = self.run_check()
        self.assertEqual(len(sent), 1)
        self.assertIn("Vuelve a funcionar: Worker del escáner", sent[0])

    def test_short_outage_is_never_reported(self):
        self.run_check([{"celery@mint": {"ok": "pong"}}])
        self.assertEqual(self.run_check()[0], [])  # se arregló antes de los 10 min

    def test_warning_alerts_at_once_and_silently(self):
        SyncRun.objects.create(status=SyncRun.Status.FAILED, error="403 de Bandai")
        sent, calls = self.run_check()
        self.assertEqual(len(sent), 1)
        self.assertIn("🟡", sent[0])
        self.assertIn("403 de Bandai", sent[0])
        self.assertTrue(calls[0]["disable_notification"])

    @override_settings(TELEGRAM_BOT_TOKEN="")
    def test_without_bot_nothing_is_sent_and_it_retries_later(self):
        from cards import alerts

        SyncRun.objects.create(status=SyncRun.Status.FAILED, error="x")
        self.assertEqual(self.run_check(), ([], []))
        self.assertFalse(cache.get(alerts.STATE_KEY)["cards_sync"]["alerted"])
