import csv
import io

from django.test import TestCase
from rest_framework.test import APIClient

from cards.models import Card
from collection.models import CollectionEntry, Location


class CollectionCsvTests(TestCase):
    """Exportar Mi colección a CSV e importar sumando copias (con vista previa)."""

    def setUp(self):
        self.champa = Card.objects.create(id=4, card_number="BT1-001", name="Champa", card_set="Galactic Battle")
        self.pr = Card.objects.create(id=1088, card_number="BT1-001", name="Champa", card_set="Promo")
        self.vados = Card.objects.create(id=7, card_number="BT1-008", name="Vados", card_set="Galactic Battle")
        self.loose = Location.default()
        self.deck = Location.objects.create(name="Mazo rojo", kind="deck")
        CollectionEntry.objects.create(card=self.champa, location=self.loose, quantity=2)
        CollectionEntry.objects.create(card=self.vados, location=self.deck, quantity=1, fake=True, notes="titular")
        self.client = APIClient()

    def preview(self, text):
        return self.client.post("/api/my-collection/import/", {"csv": text}, format="json")

    def qty(self, card, location, fake=False):
        entry = CollectionEntry.objects.filter(card=card, location=location, fake=fake).first()
        return entry.quantity if entry else 0

    def test_export(self):
        r = self.client.get("/api/my-collection/csv/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("attachment", r["Content-Disposition"])
        text = r.content.decode("utf-8")
        self.assertTrue(text.startswith("﻿"))
        rows = list(csv.reader(io.StringIO(text.lstrip("﻿")), delimiter=";"))
        self.assertEqual(rows[0], ["id", "número", "nombre", "edición", "ubicación", "cantidad", "falsa", "notas"])
        self.assertIn(["4", "BT1-001", "Champa", "Galactic Battle", "Sin ubicar", "2", "no", ""], rows)
        self.assertIn(["7", "BT1-008", "Vados", "Galactic Battle", "Mazo rojo", "1", "sí", "titular"], rows)

    def test_export_reimports_as_the_same_copies(self):
        # Exportar y volver a importar duplica exactamente lo que había (nunca borra, suma).
        text = self.client.get("/api/my-collection/csv/").content.decode("utf-8")
        r = self.client.post("/api/my-collection/import/", {"csv": text, "apply": True}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.qty(self.champa, self.loose), 4)
        self.assertEqual(self.qty(self.vados, self.deck, fake=True), 2)

    def test_preview_does_not_write(self):
        r = self.preview("número;cantidad\nBT1-008;3\n")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["totals"]["copies"], 3)
        self.assertEqual(self.qty(self.vados, self.loose), 0)

    def test_identifies_by_id_then_number_and_flags_ambiguous(self):
        text = "id;número;edición;cantidad\n1088;;;1\n;BT1-008;;2\n;BT1-001;;1\n;BT1-001;Promo;1\n;ZZ9-999;;1\n"
        data = self.preview(text).data
        self.assertEqual([(r["card_id"], r["qty"]) for r in data["rows"]], [(1088, 1), (7, 2), (1088, 1)])
        self.assertEqual([a["line"] for a in data["ambiguous"]], [4])  # BT1-001 sin edición: 2 impresiones
        self.assertEqual(len(data["errors"]), 1)  # ZZ9-999 no existe
        self.assertEqual(data["totals"]["skipped"], 2)

    def test_unknown_location_goes_to_default_with_warning(self):
        text = "id;ubicación;cantidad;falsa\n7;Caja que no existe;2;sí\n4;mazo rojo;1;no\n"
        data = self.preview(text).data
        self.assertEqual(data["totals"]["unknown_locations"], ["Caja que no existe"])
        self.assertEqual([r["location"] for r in data["rows"]], ["Sin ubicar", "Mazo rojo"])
        self.client.post("/api/my-collection/import/", {"csv": text, "apply": True}, format="json")
        self.assertEqual(self.qty(self.vados, self.loose, fake=True), 2)
        self.assertEqual(self.qty(self.champa, self.deck), 1)

    def test_comma_separated_and_english_headers(self):
        data = self.preview("number,qty,location\nBT1-008,1,Mazo rojo\n").data
        self.assertEqual([(r["card_id"], r["location"]) for r in data["rows"]], [(7, "Mazo rojo")])

    def test_invalid_rows_and_missing_columns(self):
        data = self.preview("id;cantidad\n7;abc\n7;0\n").data
        self.assertEqual(len(data["errors"]), 2)
        self.assertEqual(data["totals"]["rows"], 0)
        r = self.preview("nombre;ubicación\nVados;Mazo rojo\n")
        self.assertEqual(r.status_code, 400)
