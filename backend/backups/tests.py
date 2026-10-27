import json
import shutil
import tempfile
from pathlib import Path

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings

from . import services

PAGE = "/admin/backups/backup/"


class BackupAdminTests(TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        base, self.requests = self.root / "dbs", self.root / "request"
        (base / "daily" / "2026-10-27_0334").mkdir(parents=True)
        (base / "daily" / "2026-10-26_0331").mkdir(parents=True)
        (base / "weekly" / "2026-10-25_0332").mkdir(parents=True)
        (base / "pre-migracion").mkdir()
        self.requests.mkdir()
        (base / "daily" / "2026-10-27_0334" / "DBS.dump").write_bytes(b"x" * 1000)
        (base / "daily" / "2026-10-27_0334" / "DBS-media.tgz").write_bytes(b"y" * 5000)
        (base / "daily" / "2026-10-26_0331" / "DBS.dump").write_bytes(b"x" * 900)
        (base / "pre-migracion" / "DBS_2026-10-26_1239_antes.dump").write_bytes(b"z")
        (base / "secreto.txt").write_text("no")
        (base / "last_status.json").write_text(json.dumps({
            "status": "ok", "finished_at": "2026-10-27T03:49:16+01:00", "size": "1,5G", "remote": "ok",
            "message": "copia completa", "trigger": "programada",
        }))
        settings = override_settings(BACKUP_DIR=str(base), BACKUP_REQUEST_DIR=str(self.requests))
        settings.enable()
        self.addCleanup(settings.disable)
        self.base = base
        self.client = Client()
        self.client.force_login(User.objects.create_superuser("admin", "a@a.es", "x"))

    def test_lists_copies_newest_first_by_group(self):
        copies = services.list_copies()
        self.assertEqual([(c.group, c.name) for c in copies], [
            ("Diarias", "2026-10-27_0334"), ("Diarias", "2026-10-26_0331"),
            ("Semanales", "2026-10-25_0332"), ("Otras · pre-migracion", "DBS_2026-10-26_1239_antes.dump"),
        ])
        self.assertEqual(copies[0].size, 6000)
        self.assertEqual(copies[-1].when.strftime("%d/%m %H:%M"), "26/10 12:39")  # la fecha del nombre
        self.assertEqual([f.downloadable for f in copies[0].files], [False, True])  # el .tgz no

    def test_page(self):
        page = self.client.get(PAGE).content.decode()
        self.assertIn("Última copia correcta", page)
        self.assertIn("Hacer copia ahora", page)
        self.assertIn("daily/2026-10-27_0334/DBS.dump", page)
        self.assertNotIn('http-equiv="refresh"', page)

    def test_request_backup(self):
        self.assertEqual(self.client.get(f"{PAGE}request/").status_code, 405)
        r = self.client.post(f"{PAGE}request/")
        self.assertRedirects(r, PAGE)
        self.assertTrue((self.requests / "now").exists())
        page = self.client.get(PAGE).content.decode()
        self.assertIn("Copia pedida", page)
        self.assertIn('http-equiv="refresh"', page)  # se recarga sola hasta que acabe

    def test_running(self):
        (self.base / "running.json").write_text('{"started_at": "2026-10-27T14:02:00+01:00", "trigger": "pedida desde el admin"}')
        page = self.client.get(PAGE).content.decode()
        self.assertIn("Copia en curso", page)
        self.assertIn("pedida desde el admin", page)

    def test_download_only_dumps_inside_the_folder(self):
        r = self.client.get(f"{PAGE}download/daily/2026-10-27_0334/DBS.dump")
        self.assertEqual((r.status_code, b"".join(r.streaming_content)), (200, b"x" * 1000))
        self.assertIn("2026-10-27_0334_DBS.dump", r["Content-Disposition"])
        for bad in ("daily/2026-10-27_0334/DBS-media.tgz", "secreto.txt", "../request/now", "daily/no.dump"):
            self.assertEqual(self.client.get(f"{PAGE}download/{bad}").status_code, 404, bad)

    def test_needs_admin(self):
        self.client.logout()
        self.assertEqual(self.client.get(PAGE).status_code, 302)
        self.assertEqual(self.client.get(f"{PAGE}download/daily/2026-10-27_0334/DBS.dump").status_code, 302)

    def test_not_configured(self):
        with override_settings(BACKUP_DIR=""):
            self.assertIn("no están configuradas", self.client.get(PAGE).content.decode())
