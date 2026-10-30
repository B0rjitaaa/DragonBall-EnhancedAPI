from django.test import TestCase
from rest_framework.test import APIClient

from cards.models import Card
from cards.collection import fetch_export


class CollectionAdjustTests(TestCase):
    def setUp(self):
        from collection.models import CollectionEntry, Location

        self.Entry, self.Location = CollectionEntry, Location
        self.card = Card.objects.create(id=4, card_number="BT1-001", name="Champa")
        self.deck = Location.objects.create(name="Mazo rojo", kind="deck")
        self.binder = Location.objects.create(name="Archivador", kind="binder")
        self.client = APIClient()

    def adjust(self, **body):
        return self.client.post("/api/my-collection/adjust/", {"card_id": 4, **body}, format="json")

    def put(self, location, quantity):
        self.Entry.objects.create(card=self.card, location=location, quantity=quantity)

    def by_location(self, data):
        return {loc["name"]: loc["quantity"] for loc in data["locations"]}

    def test_add_goes_to_unplaced_by_default(self):
        self.assertEqual(self.adjust(delta=1).data["quantity"], 1)
        data = self.adjust(delta=2).data
        self.assertEqual((data["quantity"], self.by_location(data)), (3, {"Unsorted": 3}))

    def test_add_to_a_location(self):
        data = self.adjust(delta=2, location=self.deck.id).data
        self.assertEqual(self.by_location(data), {"Mazo rojo": 2})

    def test_remove_takes_unplaced_first_then_the_only_other_location(self):
        self.put(self.Location.default(), 1)
        self.put(self.deck, 3)
        data = self.adjust(delta=-2).data
        self.assertEqual(self.by_location(data), {"Mazo rojo": 2})

    def test_remove_with_copies_in_several_locations_asks_which(self):
        self.put(self.deck, 2)
        self.put(self.binder, 1)
        response = self.adjust(delta=-1)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.by_location(response.data), {"Mazo rojo": 2, "Archivador": 1})
        data = self.adjust(delta=-1, location=self.binder.id).data
        self.assertEqual(self.by_location(data), {"Mazo rojo": 2})

    def test_last_copy_removes_the_entry(self):
        self.adjust(delta=1)
        data = self.adjust(delta=-1).data
        self.assertEqual((data["quantity"], data["locations"]), (0, []))
        self.assertFalse(self.Entry.objects.exists())

    def test_remove_from_empty_is_harmless(self):
        self.assertEqual(self.adjust(delta=-1).data["quantity"], 0)

    def test_validation(self):
        self.assertEqual(self.adjust(delta=0).status_code, 400)
        response = self.client.post("/api/my-collection/adjust/", {"card_id": 999, "delta": 1}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_move_keeps_the_total(self):
        self.put(self.Location.default(), 6)
        move = lambda **b: self.client.post(  # noqa: E731
            "/api/my-collection/move/", {"card_id": 4, **b}, format="json"
        )
        move(source=self.Location.default().id, target=self.deck.id, quantity=4)
        data = move(source=self.Location.default().id, target=self.binder.id, quantity=1).data
        self.assertEqual(data["quantity"], 6)
        self.assertEqual(self.by_location(data), {"Unsorted": 1, "Mazo rojo": 4, "Archivador": 1})
        too_many = move(source=self.binder.id, target=self.deck.id, quantity=2)
        self.assertEqual(too_many.status_code, 400)

    def test_note_per_location(self):
        self.put(self.binder, 1)
        data = self.client.post(
            "/api/my-collection/note/", {"card_id": 4, "location": self.binder.id, "notes": "página 12"}, format="json"
        ).data
        self.assertEqual(data["locations"][0]["notes"], "página 12")


class FakeCopiesTests(TestCase):
    """Copias falsas: se marcan moviéndolas a la misma ubicación con fake=True."""

    def setUp(self):
        from collection.models import CollectionEntry, Location

        self.Entry, self.Location = CollectionEntry, Location
        self.card = Card.objects.create(id=4, card_number="BT1-001", name="Champa")
        self.deck = Location.objects.create(name="Mazo rojo", kind="deck")
        self.client = APIClient()
        self.Entry.objects.create(card=self.card, location=self.deck, quantity=4)

    def post(self, path, **body):
        return self.client.post(f"/api/my-collection/{path}/", {"card_id": 4, **body}, format="json")

    def rows(self, data):
        return [(loc["name"], loc["fake"], loc["quantity"]) for loc in data["locations"]]

    def test_existing_copies_are_genuine_by_default(self):
        self.assertFalse(self.Entry.objects.get().fake)
        self.assertFalse(fetch_export()[0]["fake"])

    def test_mark_and_unmark_fake_in_the_same_location(self):
        data = self.post("move", source=self.deck.id, target=self.deck.id, quantity=1, target_fake=True).data
        self.assertEqual(self.rows(data), [("Mazo rojo", False, 3), ("Mazo rojo", True, 1)])
        self.assertEqual((data["quantity"], data["fakes"]), (4, 1))
        data = self.post("move", source=self.deck.id, target=self.deck.id, quantity=1, source_fake=True, target_fake=False).data
        self.assertEqual(self.rows(data), [("Mazo rojo", False, 4)])

    def test_fakes_keep_being_fake_when_moved_and_removed_last(self):
        binder = self.Location.objects.create(name="Archivador", kind="binder")
        self.post("move", source=self.deck.id, target=self.deck.id, quantity=2, target_fake=True)
        data = self.post("move", source=self.deck.id, target=binder.id, quantity=1, source_fake=True).data
        self.assertIn(("Archivador", True, 1), self.rows(data))
        # Restar sin decir cuál quita primero las auténticas…
        data = self.post("adjust", delta=-1, location=self.deck.id).data
        self.assertEqual(self.rows(data), [("Archivador", True, 1), ("Mazo rojo", False, 1), ("Mazo rojo", True, 1)])
        # …y con fake=True, las falsas.
        data = self.post("adjust", delta=-1, location=self.deck.id, fake=True).data
        self.assertEqual(self.rows(data), [("Archivador", True, 1), ("Mazo rojo", False, 1)])

    def test_location_totals_and_filter(self):
        self.post("move", source=self.deck.id, target=self.deck.id, quantity=1, target_fake=True)
        deck = next(loc for loc in self.client.get("/api/my-collection/locations/").data if loc["name"] == "Mazo rojo")
        self.assertEqual((deck["cards"], deck["copies"], deck["fakes"]), (1, 4, 1))
        fakes = self.client.post("/api/cards/search/", {"scope": "collection", "fake": True}, format="json").data
        self.assertEqual([(r["id"], r["quantity"]) for r in fakes["results"]], [(4, 1)])

    def test_deleting_a_location_keeps_fakes_apart(self):
        self.post("move", source=self.deck.id, target=self.deck.id, quantity=1, target_fake=True)
        self.client.delete(f"/api/my-collection/locations/{self.deck.id}/")
        self.assertEqual(
            sorted(self.Entry.objects.values_list("location__name", "fake", "quantity")),
            [("Unsorted", False, 3), ("Unsorted", True, 1)],
        )

    def test_marking_a_specific_binder_copy_as_fake_takes_its_position(self):
        binder = self.Location.objects.create(name="Archivador", kind="binder")
        self.Entry.objects.create(
            card=self.card, location=binder, quantity=2, notes="Pág. 58 · fila 2 · col 2\nPág. 74 · fila 3 · col 3"
        )
        data = self.post("move", source=binder.id, target=binder.id, quantity=1, target_fake=True,
                         note_line="Pág. 74 · fila 3 · col 3").data
        rows = {(loc["name"], loc["fake"]): (loc["quantity"], loc["notes"]) for loc in data["locations"]}
        self.assertEqual(rows[("Archivador", False)], (1, "Pág. 58 · fila 2 · col 2"))
        self.assertEqual(rows[("Archivador", True)], (1, "Pág. 74 · fila 3 · col 3"))
        bad = self.post("move", source=binder.id, target=binder.id, quantity=1, target_fake=True, note_line="Pág. 1")
        self.assertEqual(bad.status_code, 400)

    def test_note_per_genuine_or_fake_row(self):
        self.post("move", source=self.deck.id, target=self.deck.id, quantity=1, target_fake=True)
        data = self.post("note", location=self.deck.id, fake=True, notes="AliExpress, junio").data
        self.assertEqual([loc["notes"] for loc in data["locations"]], ["", "AliExpress, junio"])


class ReorderTests(TestCase):
    """«Mi orden»: posición de cada carta dentro de su ubicación."""

    def setUp(self):
        from collection.models import CollectionEntry, Location

        self.Entry, self.Location = CollectionEntry, Location
        self.deck = Location.objects.create(name="Mazo", kind="deck")
        self.cards = [Card.objects.create(id=i, card_number=f"BT1-00{i}", name=f"C{i}") for i in range(1, 5)]
        for c in self.cards:
            CollectionEntry.objects.create(card=c, location=self.deck, quantity=1)
        self.client = APIClient()

    def order(self):
        return list(self.Entry.objects.filter(location=self.deck, fake=False).order_by("position").values_list("card_id", flat=True))

    def test_new_cards_go_last_and_fake_row_shares_position(self):
        self.assertEqual(self.order(), [1, 2, 3, 4])
        fake = self.Entry.objects.create(card=self.cards[1], location=self.deck, quantity=1, fake=True)
        self.assertEqual(fake.position, self.Entry.objects.get(card=self.cards[1], fake=False).position)

    def test_reorder_a_subset_keeps_the_rest_in_place(self):
        r = self.client.post("/api/my-collection/reorder/", {"location": self.deck.id, "card_ids": [4, 2]}, format="json")
        self.assertEqual(r.status_code, 204)
        self.assertEqual(self.order(), [1, 4, 3, 2])  # 4 y 2 intercambian sus huecos; 1 y 3 no se mueven
        self.client.post("/api/my-collection/reorder/", {"location": self.deck.id, "card_ids": [3, 1, 4, 2]}, format="json")
        self.assertEqual(self.order(), [3, 1, 4, 2])

    def test_old_data_with_equal_positions_is_numbered_first(self):
        self.Entry.objects.update(position=0)
        self.client.post("/api/my-collection/reorder/", {"location": self.deck.id, "card_ids": [2, 1]}, format="json")
        self.assertEqual(self.order(), [2, 1, 3, 4])


class LocationTests(TestCase):
    def setUp(self):
        from collection.models import CollectionEntry, Location

        self.Entry, self.Location = CollectionEntry, Location
        self.client = APIClient()
        self.card = Card.objects.create(id=4, card_number="BT1-001", name="Champa")

    def test_list_always_includes_unplaced_with_totals(self):
        deck = self.client.post("/api/my-collection/locations/", {"name": "Mazo rojo", "kind": "deck"}, format="json").data
        self.Entry.objects.create(card=self.card, location_id=deck["id"], quantity=4)
        data = self.client.get("/api/my-collection/locations/").data
        self.assertEqual([(loc["name"], loc["copies"]) for loc in data], [("Unsorted", 0), ("Mazo rojo", 4)])
        self.assertTrue(data[0]["is_default"])

    def test_deleting_a_location_sends_its_copies_to_unplaced(self):
        deck = self.Location.objects.create(name="Mazo rojo")
        self.Entry.objects.create(card=self.card, location=self.Location.default(), quantity=2)
        self.Entry.objects.create(card=self.card, location=deck, quantity=4)
        self.assertEqual(self.client.delete(f"/api/my-collection/locations/{deck.id}/").status_code, 204)
        self.assertEqual(list(self.Entry.objects.values_list("location__name", "quantity")), [("Unsorted", 6)])

    def test_unplaced_cannot_be_deleted(self):
        default = self.Location.default()
        self.assertEqual(self.client.delete(f"/api/my-collection/locations/{default.id}/").status_code, 400)


class RestoreBackupTests(TestCase):
    """Restaurar la copia JSON («Descargar copia») sustituyendo la colección: vista previa y aplicación."""

    def setUp(self):
        from collection.models import CollectionEntry, Location
        from decks.models import SideCard

        self.Entry, self.Location, self.Side = CollectionEntry, Location, SideCard
        self.goku = Card.objects.create(id=1, card_number="BT1-001", name="Goku")
        self.vegeta = Card.objects.create(id=2, card_number="BT1-002", name="Vegeta")
        self.cell = Card.objects.create(id=3, card_number="BT1-003", name="Cell")
        self.deck = Location.objects.create(name="Mazo rojo", kind="deck")
        self.box = Location.objects.create(name="Caja 1", kind="storage")
        self.client = APIClient()
        # La copia: 4 Goku y 1 Vegeta falsa en el mazo, 2 Cell en una caja nueva.
        self.Entry.objects.create(card=self.goku, location=self.deck, quantity=4, notes="pág. 1")
        self.Entry.objects.create(card=self.vegeta, location=self.deck, quantity=1, fake=True)
        self.Entry.objects.create(card=self.cell, location=self.box, quantity=2)
        self.backup = self.client.get("/api/my-collection/backup/").json()
        self.backup["locations"].append({"name": "Caja nueva", "kind": "almacén", "notes": "armario"})
        for row in self.backup["cards"]:
            if row["id"] == 3:
                row["location"] = "Caja nueva"
        self.backup["cards"].append({"id": 999, "number": "XX-1", "name": "Inventada", "qty": 1, "location": ""})
        # Lo actual (después de la copia): se ha perdido Goku del mazo y hay 3 Vegeta en la caja.
        self.Entry.objects.filter(card=self.goku).delete()
        self.Entry.objects.create(card=self.vegeta, location=self.box, quantity=3)
        self.Side.objects.create(deck=self.deck, card=self.vegeta, quantity=1)
        self.Side.objects.create(deck=self.box, card=self.vegeta, quantity=3)

    def restore(self, apply=False, backup=None):
        return self.client.post("/api/my-collection/restore/", {"backup": backup or self.backup, "apply": apply},
                                format="json")

    def state(self):
        return {(e.card_id, e.location.name, e.fake): e.quantity for e in self.Entry.objects.select_related("location")}

    def test_preview_shows_what_changes_without_touching_anything(self):
        before = self.state()
        data = self.restore().json()
        self.assertEqual(self.state(), before)
        self.assertEqual((data["before"]["copies"], data["after"]["copies"]), (6, 7))
        self.assertEqual((data["added"], data["removed"]), (6, 5))  # +4 Goku +2 Cell nueva · −3 Vegeta −2 Cell caja
        self.assertEqual(data["create_locations"], ["Caja nueva"])
        self.assertEqual(data["emptied_locations"], ["Caja 1"])
        self.assertEqual(data["skipped"], [{"card": "XX-1 Inventada", "reason": "not in the catalog"}])
        self.assertIn({"card_id": 1, "number": "BT1-001", "name": "Goku", "location": "Mazo rojo", "fake": False,
                       "before": 0, "after": 4}, data["changes"])

    def test_apply_replaces_the_collection(self):
        data = self.restore(apply=True).json()
        self.assertEqual(data["applied"]["copies"], 7)
        self.assertEqual(self.state(), {(1, "Mazo rojo", False): 4, (2, "Mazo rojo", True): 1, (3, "Caja nueva", False): 2})
        new = self.Location.objects.get(name="Caja nueva")
        self.assertEqual((new.kind, new.notes), ("storage", "armario"))
        self.assertTrue(self.Location.objects.filter(name="Caja 1").exists())  # se vacía, no se borra
        self.assertEqual(self.Entry.objects.get(card=self.goku).notes, "pág. 1")
        # Side deck: en el mazo sigue (hay 1 Vegeta); en la caja ya no hay Vegeta.
        self.assertEqual(list(self.Side.objects.values_list("deck__name", "quantity")), [("Mazo rojo", 1)])
        self.assertEqual(self.restore().json()["changes_total"], 0)  # restaurada: ya no hay diferencias

    def test_old_backups_in_spanish_use_the_default_location(self):
        # Copias anteriores: la ubicación por defecto se llamaba «Sin ubicar» y los tipos iban en español.
        backup = {"format": "dbs-collection", "locations": [{"name": "Sin ubicar", "kind": "otro"},
                                                            {"name": "Archivador azul", "kind": "archivador"}],
                  "cards": [{"id": 1, "qty": 2, "location": "Sin ubicar"},
                            {"id": 2, "qty": 1, "location": "Archivador azul"}]}
        self.restore(apply=True, backup=backup)
        self.assertEqual(self.state(), {(1, "Unsorted", False): 2, (2, "Archivador azul", False): 1})
        self.assertFalse(self.Location.objects.filter(name="Sin ubicar").exists())
        self.assertEqual(self.Location.objects.get(name="Archivador azul").kind, "binder")

    def test_binder_size_goes_in_the_backup_and_comes_back(self):
        self.Location.objects.create(name="Archivador 4x3", kind="binder", binder_rows=4, binder_cols=3)
        backup = self.client.get("/api/my-collection/backup/").json()
        place = next(p for p in backup["locations"] if p["name"] == "Archivador 4x3")
        self.assertEqual(place["pockets"], "4x3")
        self.Location.objects.filter(name="Archivador 4x3").delete()
        self.restore(apply=True, backup=backup)
        binder = self.Location.objects.get(name="Archivador 4x3")
        self.assertEqual((binder.kind, binder.binder_rows, binder.binder_cols), ("binder", 4, 3))

    def test_rejects_other_files(self):
        response = self.restore(backup={"cards": []})
        self.assertEqual(response.status_code, 400)
        self.assertIn("dbs-collection", response.json()["detail"])


class BinderSizeTests(TestCase):
    """Archivadores: bolsillos por página al crearlos y al editarlos."""

    def setUp(self):
        self.client = APIClient()

    def test_create_and_change_the_size(self):
        created = self.client.post("/api/my-collection/locations/",
                                   {"name": "Archivador 4x4", "kind": "binder", "binder_rows": 4, "binder_cols": 4},
                                   format="json")
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual((created.data["binder_rows"], created.data["binder_cols"]), (4, 4))
        pk = created.data["id"]
        changed = self.client.patch(f"/api/my-collection/locations/{pk}/", {"binder_rows": 5, "binder_cols": 2},
                                    format="json")
        self.assertEqual((changed.data["binder_rows"], changed.data["binder_cols"]), (5, 2))
        too_big = self.client.patch(f"/api/my-collection/locations/{pk}/", {"binder_rows": 7}, format="json")
        self.assertEqual(too_big.status_code, 400)

    def test_default_is_3x3(self):
        created = self.client.post("/api/my-collection/locations/", {"name": "Archivador", "kind": "binder"},
                                   format="json")
        self.assertEqual((created.data["binder_rows"], created.data["binder_cols"]), (3, 3))
