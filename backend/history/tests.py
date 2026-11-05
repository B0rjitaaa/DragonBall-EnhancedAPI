from django.test import TestCase
from rest_framework.test import APIClient

from cards.models import Card
from collection.models import CollectionEntry, Location
from decks.models import DeckVersion, Match, SideCard

from . import recorder
from .models import Activity, RestorePoint


def qty(card, location, fake=False):
    e = CollectionEntry.objects.filter(card=card, location=location, fake=fake).first()
    return e.quantity if e else 0


class HistoryTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.leader = Card.objects.create(id=1, card_number="EX20-01", name="Cell", card_type="LEADER")
        self.a = Card.objects.create(id=2, card_number="BT29-86", name="Goku Black", card_type="BATTLE")
        self.b = Card.objects.create(id=4, card_number="EX20-03", name="Android 17", card_type="BATTLE")
        self.box = Location.objects.create(name="Caja 1", kind="storage")
        self.binder = Location.objects.create(name="Archivador", kind="binder")
        self.other = Location.objects.create(name="Mazo viejo", kind="deck")
        CollectionEntry.objects.create(card=self.leader, location=self.binder, quantity=1, notes="P. 3 · row 1 · col 2")
        CollectionEntry.objects.create(card=self.a, location=self.binder, quantity=2, notes="P. 5 · row 1 · col 1\nP. 5 · row 1 · col 2")
        CollectionEntry.objects.create(card=self.a, location=self.other, quantity=2)
        CollectionEntry.objects.create(card=self.b, location=self.box, quantity=3)

    def adjust(self, card, delta, location):
        return self.api.post("/api/my-collection/adjust/", {"card_id": card.id, "delta": delta, "location": location.id}, format="json")

    def history(self, **params):
        return self.api.get("/api/history/", params).json()

    def undo(self, activity_id):
        return self.api.post(f"/api/history/{activity_id}/undo/")

    def test_clicks_in_a_row_are_one_change_and_undo(self):
        for _ in range(3):
            self.assertEqual(self.adjust(self.b, 1, self.box).status_code, 200)
        data = self.history()
        self.assertEqual(data["count"], 1)  # tres «+» seguidos: una sola acción
        act = data["results"][0]
        self.assertEqual((act["added"], act["kind"]), (3, "adjust"))
        self.assertIn("+3 EX20-03", act["title"])
        self.assertEqual(qty(self.b, self.box), 6)
        self.assertEqual(self.undo(act["id"]).status_code, 200)
        self.assertEqual(qty(self.b, self.box), 3)
        self.assertIsNotNone(Activity.objects.get(pk=act["id"]).undone_at)
        self.assertEqual(self.history()["results"][0]["kind"], "undo")
        self.assertEqual(self.undo(act["id"]).status_code, 400)  # ya deshecha

    def test_undo_brings_back_a_card_that_was_removed_with_its_notes(self):
        self.api.post("/api/my-collection/adjust/", {"card_id": 1, "delta": -1, "location": self.binder.id}, format="json")
        self.assertEqual(qty(self.leader, self.binder), 0)
        self.undo(self.history()["results"][0]["id"])
        entry = CollectionEntry.objects.get(card=self.leader, location=self.binder)
        self.assertEqual((entry.quantity, entry.notes), (1, "P. 3 · row 1 · col 2"))

    def test_conflict_when_the_same_cards_changed_later(self):
        self.adjust(self.b, 1, self.box)
        first = self.history()["results"][0]["id"]
        r = self.api.post("/api/my-collection/move/", {"card_id": 4, "source": self.box.id, "target": self.binder.id,
                                                       "quantity": 4}, format="json")
        self.assertEqual(r.status_code, 200)
        later = self.history()["results"][0]["id"]
        check = self.api.get(f"/api/history/{first}/undo/").json()
        self.assertFalse(check["ok"])
        self.assertEqual([a["id"] for a in check["later"]], [later])
        r = self.undo(first)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(qty(self.b, self.binder), 4)  # no se ha tocado nada
        # Deshecha la posterior, ya se puede.
        self.assertEqual(self.undo(later).status_code, 200)
        self.assertEqual(self.undo(first).status_code, 200)
        self.assertEqual((qty(self.b, self.box), qty(self.b, self.binder)), (3, 0))

    def test_undo_a_deck_import_puts_every_copy_back(self):
        text = "Cell [EX20-01]\n4 Goku Black [BT29-086]"
        lines = self.api.post("/api/my-collection/decks/import/preview/", {"source": text}, format="json").json()["lines"]
        r = self.api.post("/api/my-collection/decks/import/", {"lines": lines, "name": "Cell nuevo",
                                                              "take_from": [self.other.id]}, format="json")
        self.assertEqual(r.status_code, 201)
        deck = Location.objects.get(name="Cell nuevo")
        self.assertEqual((qty(self.a, deck), qty(self.a, self.binder), qty(self.a, self.other)), (4, 0, 0))
        act = self.history()["results"][0]
        self.assertEqual(act["title"], "Imported deck “Cell nuevo”")
        self.assertTrue(act["restore_point"])
        detail = self.api.get(f"/api/history/{act['id']}/").json()
        self.assertIn("Created deck “Cell nuevo”", detail["other"])
        self.assertTrue(any("Mazo viejo" in o for o in detail["other"]))  # el mazo que cedió cartas guardó versión
        self.assertEqual(self.undo(act["id"]).status_code, 200)
        self.assertFalse(Location.objects.filter(name="Cell nuevo").exists())
        self.assertFalse(DeckVersion.objects.filter(deck=self.other).exists())
        binder_entry = CollectionEntry.objects.get(card=self.a, location=self.binder)
        self.assertEqual((binder_entry.quantity, binder_entry.notes), (2, "P. 5 · row 1 · col 1\nP. 5 · row 1 · col 2"))
        self.assertEqual((qty(self.a, self.other), qty(self.leader, self.binder)), (2, 1))

    def test_undo_deleting_a_deck_brings_back_its_lists(self):
        SideCard.objects.create(deck=self.other, card=self.a, quantity=1)
        version = DeckVersion.objects.create(deck=self.other, number=1, principal=True)
        version.cards.create(card=self.a, section="main", quantity=2)
        uid = self.other.uid
        r = self.api.delete(f"/api/my-collection/locations/{self.other.id}/")
        self.assertIn(r.status_code, (200, 204))
        self.assertFalse(Location.objects.filter(pk=self.other.pk).exists())
        act = self.history()["results"][0]
        self.assertEqual(act["kind"], "location_delete")
        self.assertIn("Deleted deck “Mazo viejo”", act["title"])
        self.assertIn("2× BT29-86 Mazo viejo → Unsorted", act["title"])
        self.undo(act["id"])
        deck = Location.objects.get(pk=self.other.pk)
        self.assertEqual((deck.uid, deck.name), (uid, "Mazo viejo"))
        self.assertEqual(qty(self.a, deck), 2)
        self.assertEqual(qty(self.a, Location.default()), 0)
        self.assertEqual(SideCard.objects.get().quantity, 1)
        self.assertTrue(DeckVersion.objects.get().principal)
        self.assertEqual(DeckVersion.objects.get().cards.get().quantity, 2)

    def test_matches_deleted_in_cascade_come_back(self):
        # Borrar un mazo desde el admin se lleva sus listas y partidas en cascada: deshacerlo las recupera.
        version = DeckVersion.objects.create(deck=self.other, number=1, principal=True)
        Match.objects.create(version=version, played_on="2026-11-01", result="win", opponent_leader_name="Goku")
        with recorder.record("admin", source="admin") as rec:
            CollectionEntry.objects.filter(location=self.other).delete()
            Location.objects.filter(pk=self.other.pk).delete()
        self.assertFalse(Match.objects.exists())
        recorder.undo(rec.activity)
        self.assertEqual(Match.objects.get().version.deck_id, self.other.pk)
        self.assertEqual(qty(self.a, self.other), 2)

    def test_filter_by_card_and_location(self):
        self.adjust(self.b, 1, self.box)
        self.api.post("/api/my-collection/move/", {"card_id": 2, "source": self.binder.id, "target": self.box.id,
                                                   "quantity": 1}, format="json")
        self.assertEqual(self.history()["count"], 2)
        self.assertEqual([a["kind"] for a in self.history(card=2)["results"]], ["move"])
        self.assertEqual(self.history(location=self.binder.id)["count"], 1)
        self.assertEqual(self.history(location=self.box.id)["count"], 2)
        self.assertEqual(self.history(q="Android")["count"], 1)

    def test_restore_point(self):
        with recorder.record("csv_import", title="Imported CSV", restore_point=True):
            CollectionEntry.objects.filter(card=self.b).update(quantity=10)
            CollectionEntry.objects.create(card=self.leader, location=self.box, quantity=2)
        self.adjust(self.a, 1, self.box)
        point = RestorePoint.objects.get()
        preview = self.api.get(f"/api/history/restore-points/{point.id}/").json()
        self.assertEqual((preview["added"], preview["removed"]), (0, 10))  # vuelve: −7 Android 17, −2 Cell, −1 Goku
        r = self.api.post(f"/api/history/restore-points/{point.id}/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual((qty(self.b, self.box), qty(self.leader, self.box), qty(self.a, self.box)), (3, 0, 0))
        # Volver a un punto también se puede deshacer.
        self.undo(r.json()["activity"]["id"])
        self.assertEqual(qty(self.b, self.box), 10)

    def test_nothing_changed_nothing_recorded(self):
        self.api.post("/api/my-collection/import/", {"csv": "card,quantity\nEX20-03,1\n"}, format="json")  # vista previa
        self.assertEqual(self.history()["count"], 0)
        self.assertFalse(RestorePoint.objects.exists())

    def test_redo_and_undo_again(self):
        self.adjust(self.b, 2, self.box)
        change = self.history()["results"][0]["id"]
        self.undo(change)
        undo_row, changed_row = self.history()["results"][:2]
        self.assertEqual((undo_row["kind"], changed_row["redo_id"]), ("undo", undo_row["id"]))
        # Rehacer = deshacer el «Undo»: vuelven las copias y el cambio original deja de estar deshecho.
        self.assertEqual(self.undo(undo_row["id"]).status_code, 200)
        self.assertEqual(qty(self.b, self.box), 5)
        redo = self.history()["results"][0]
        self.assertEqual((redo["kind"], redo["title"]), ("redo", "Redo: Copies: +2 EX20-03 → Caja 1"))
        self.assertIsNone(Activity.objects.get(pk=change).undone_at)
        self.assertIsNone(self.history(kind="adjust")["results"][0]["redo_id"])
        # Y se puede volver a deshacer (deshaciendo el «Redo»), y a rehacer otra vez.
        self.undo(redo["id"])
        self.assertEqual(qty(self.b, self.box), 3)
        self.assertIsNotNone(Activity.objects.get(pk=change).undone_at)
        again = self.history(kind="adjust")["results"][0]["redo_id"]
        self.assertEqual(self.undo(again).status_code, 200)
        self.assertEqual(qty(self.b, self.box), 5)

    def test_redo_is_blocked_if_the_cards_changed(self):
        self.adjust(self.b, 2, self.box)
        self.undo(self.history()["results"][0]["id"])
        undo_id = self.history()["results"][0]["id"]
        self.adjust(self.b, 1, self.box)  # las mismas copias cambian después
        self.assertEqual(self.undo(undo_id).status_code, 409)
        self.assertEqual(qty(self.b, self.box), 4)

    def test_csv_export(self):
        self.api.post("/api/my-collection/move/", {"card_id": 2, "source": self.binder.id, "target": self.box.id,
                                                   "quantity": 1}, format="json")
        r = self.api.get("/api/history/csv/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("attachment", r["Content-Disposition"])
        lines = r.content.decode("utf-8-sig").splitlines()
        self.assertTrue(lines[0].startswith("date;change_id;type;change"))
        rows = [line.split(";") for line in lines[1:]]
        by_place = {row[8]: row for row in rows}
        self.assertEqual(by_place["Archivador"][10:13], ["2", "1", "-1"])
        self.assertEqual(by_place["Caja 1"][10:13], ["0", "1", "1"])
        self.assertEqual(by_place["Archivador"][6], "BT29-86")
        # Con filtros, solo lo filtrado.
        self.assertEqual(len(self.api.get("/api/history/csv/", {"card": 4}).content.decode("utf-8-sig").splitlines()), 1)
