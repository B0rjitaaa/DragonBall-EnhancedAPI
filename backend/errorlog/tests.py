import logging
from datetime import timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from . import tasks
from .handler import DatabaseHandler
from .models import ErrorGroup

logger = logging.getLogger("dbs.test")


def fail(value):
    raise ValueError(f"valor raro: {value}")


@override_settings(TELEGRAM_BOT_TOKEN="t", TELEGRAM_CHAT_ID="c")
class ErrorLogTests(TestCase):
    def setUp(self):
        notify = mock.patch("errorlog.tasks.notify_error.apply_async")
        self.notify = notify.start()
        self.addCleanup(notify.stop)

    def log_failure(self, value):
        try:
            fail(value)
        except ValueError:
            logger.exception("Algo ha fallado")

    def notified(self):
        return [c.args[0][1] for c in self.notify.call_args_list]

    def test_same_cause_is_one_group(self):
        self.log_failure(1)
        self.log_failure(2)  # otro mensaje, misma causa
        group = ErrorGroup.objects.get()
        self.assertEqual((group.source, group.kind, group.count), ("server", "ValueError", 2))
        self.assertIn("valor raro: 2", group.message)
        self.assertIn("errorlog/tests.py", group.where)
        self.assertIn("in fail", group.traceback)
        self.assertEqual(self.notified(), ["nuevo"])  # solo se avisa la primera vez

    def test_resolved_error_reopens_and_notifies(self):
        self.log_failure(1)
        ErrorGroup.objects.update(resolved_at=timezone.now())
        self.log_failure(1)
        self.assertIsNone(ErrorGroup.objects.get().resolved_at)
        self.assertEqual(self.notified(), ["nuevo", "vuelve"])

    def test_error_without_exception_and_warnings(self):
        logger.warning("Esto no es un error")
        logger.error("No se pudo leer %s", "BT1-001")
        logger.error("No se pudo leer %s", "BT2-002")
        group = ErrorGroup.objects.get()
        self.assertEqual((group.kind, group.count, group.message), ("dbs.test", 2, "No se pudo leer BT2-002"))

    def test_server_error_is_recorded_with_its_request(self):
        client = Client(raise_request_exception=False)
        with mock.patch("cards.views.LocationsView.get", side_effect=RuntimeError("boom")):
            r = client.get("/api/my-collection/locations/?x=1", HTTP_USER_AGENT="Firefox")
        self.assertEqual(r.status_code, 500)
        group = ErrorGroup.objects.get()
        self.assertEqual((group.kind, group.request, group.user_agent), ("RuntimeError", "GET /api/my-collection/locations/?x=1", "Firefox"))

    def test_worker_source(self):
        handler = DatabaseHandler(source="worker")
        try:
            fail(1)
        except ValueError:
            import sys

            handler.emit(logging.LogRecord("celery", logging.ERROR, __file__, 1, "Task falló", (), sys.exc_info()))
        self.assertEqual(ErrorGroup.objects.get().source, "worker")

    def test_web_errors(self):
        api = APIClient()
        body = {"kind": "TypeError", "message": "x is undefined", "where": "index-abc.js:1:200",
                "stack": "TypeError: x is undefined\n at f (index-abc.js:1:200)", "page": "/locations"}
        self.assertEqual(api.post("/api/errors/", body, format="json").status_code, 204)
        api.post("/api/errors/", body, format="json")
        group = ErrorGroup.objects.get()
        self.assertEqual((group.source, group.count, group.request), ("web", 2, "/locations"))
        self.assertEqual(api.post("/api/errors/", {}, format="json").status_code, 400)

    def test_telegram_message(self):
        self.log_failure(1)
        group = ErrorGroup.objects.get()
        with mock.patch("cards.alerts.requests.post", return_value=mock.Mock(ok=True)) as post:
            self.assertTrue(tasks.notify_error(group.pk, "nuevo"))
        data = post.call_args.kwargs["data"]
        self.assertTrue(data["disable_notification"])
        self.assertIn("Error nuevo", data["text"])
        self.assertIn(f"/admin/errorlog/errorgroup/{group.pk}/change/", data["text"])

    def test_purge_only_old_resolved(self):
        old = timezone.now() - timedelta(days=91)
        for i, resolved in enumerate([old, timezone.now(), None]):
            ErrorGroup.objects.create(signature=str(i), source="server", kind="E", message="m", resolved_at=resolved)
        self.assertEqual(tasks.purge_resolved_errors(), 1)
        self.assertEqual(ErrorGroup.objects.count(), 2)

    def test_admin_shows_pending_by_default(self):
        ErrorGroup.objects.create(signature="a", source="server", kind="PendingError", message="m")
        ErrorGroup.objects.create(signature="b", source="server", kind="SolvedError", message="m", resolved_at=timezone.now())
        client = Client()
        client.force_login(User.objects.create_superuser("admin", "a@a.es", "x"))
        page = client.get("/admin/errorlog/errorgroup/").content.decode()
        self.assertIn("PendingError", page)
        self.assertNotIn("SolvedError", page)
        self.assertIn("SolvedError", client.get("/admin/errorlog/errorgroup/?estado=todos").content.decode())
