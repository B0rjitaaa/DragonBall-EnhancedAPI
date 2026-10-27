import json

from django.test import TestCase
from rest_framework.test import APIClient

from cards.models import Card
from collection.models import CollectionEntry, Location


class MyCollectionTests(TestCase):
    """Mi colección = el buscador con scope=collection, y sus acciones sobre las copias."""

    def setUp(self):
        self.champa = Card.objects.create(id=4, card_number="BT1-001", name="Champa", card_type="LEADER", colors=["Red"])
        self.pr = Card.objects.create(id=1088, card_number="BT1-005", name="Champa PR", card_type="BATTLE", colors=["Red"])
        self.vados = Card.objects.create(id=7, card_number="BT1-008", name="Vados", card_type="BATTLE", colors=["Blue"])
        self.loose = Location.default()
        self.deck = Location.objects.create(name="Mazo rojo", kind="deck", notes="funda roja")
        self.box = Location.objects.create(name="Caja vacía", kind="storage")
        CollectionEntry.objects.create(card=self.champa, location=self.loose, quantity=2)
        CollectionEntry.objects.create(card=self.champa, location=self.deck, quantity=1, notes="titular")
        CollectionEntry.objects.create(card=self.pr, location=self.loose, quantity=1)
        CollectionEntry.objects.create(card=self.pr, location=self.deck, quantity=1, fake=True)
        self.client = APIClient()

    def search(self, **body):
        return self.client.post("/api/cards/search/", body, format="json")

    def post(self, path, body):
        return self.client.post(f"/api/my-collection/{path}", body, format="json")

    def qty(self, card, location, fake=False):
        entry = CollectionEntry.objects.filter(card=card, location=location, fake=fake).first()
        return entry.quantity if entry else 0

    def test_search_in_collection_only_returns_owned_cards_with_copies(self):
        data = self.search(scope="collection").data
        self.assertEqual(sorted(r["card_number"] for r in data["results"]), ["BT1-001", "BT1-005"])
        champa = next(r for r in data["results"] if r["id"] == 4)
        self.assertEqual(champa["quantity"], 3)
        self.assertEqual(
            [(loc["name"], loc["quantity"], loc["notes"]) for loc in champa["locations"]],
            [("Sin ubicar", 2, ""), ("Mazo rojo", 1, "titular")],
        )
        self.assertEqual(data["total_copies"], 4)  # por defecto, sin la falsa
        pr = next(r for r in data["results"] if r["id"] == 1088)
        self.assertEqual((pr["quantity"], pr["total_quantity"], pr["fakes"]), (1, 2, 1))
        self.assertEqual(self.search(scope="collection", include_fakes=True).data["total_copies"], 5)
        self.assertEqual(data["missing"], [])

    def test_filters_apply_inside_the_collection(self):
        query = {"op": "and", "children": [{"field": "type", "operator": "in", "value": ["LEADER"]}]}
        data = self.search(scope="collection", query=query).data
        self.assertEqual([r["card_number"] for r in data["results"]], ["BT1-001"])
        self.assertEqual(data["total_copies"], 3)

    def test_location_filter_shows_the_copies_there(self):
        data = self.search(scope="collection", location=self.deck.id).data
        # En el mazo hay una Champa auténtica y una Champa PR falsa: por defecto, solo la auténtica.
        self.assertEqual([(r["card_number"], r["quantity"]) for r in data["results"]], [("BT1-001", 1)])
        data = self.search(scope="collection", location=self.deck.id, include_fakes=True).data
        self.assertEqual([(r["card_number"], r["quantity"]) for r in data["results"]], [("BT1-001", 1), ("BT1-005", 1)])
        self.assertEqual(data["results"][0]["total_quantity"], 3)
        self.assertEqual(self.client.get(f"/api/facets/?scope=collection&location={self.deck.id}").data["total"], 1)
        facets = self.client.get(f"/api/facets/?scope=collection&location={self.deck.id}&include_fakes=true").data
        self.assertEqual(facets["total"], 2)

    def test_fake_filter_shows_only_cards_with_fake_copies(self):
        data = self.search(scope="collection", fake=True).data
        self.assertEqual([(r["card_number"], r["quantity"], r["total_quantity"]) for r in data["results"]], [("BT1-005", 1, 2)])
        self.assertEqual(self.search(scope="collection", fake=True, location=self.loose.id).data["count"], 0)
        self.assertEqual(self.client.get("/api/facets/?scope=collection&fake=true").data["total"], 1)
        self.assertEqual(self.client.get("/api/facets/?scope=collection&fake=quizá").status_code, 400)

    def test_marking_fake_is_a_move_to_the_same_location(self):
        CollectionEntry.objects.filter(card=self.champa, location=self.deck).update(notes="Pág. 74 · fila 3 · col 3\notra")
        data = self.post("move/", {"card_id": 4, "source": self.deck.id, "target": self.deck.id, "quantity": 1,
                                   "target_fake": True, "note_line": "Pág. 74 · fila 3 · col 3"}).data
        self.assertEqual((data["quantity"], data["fakes"]), (3, 1))
        fake = CollectionEntry.objects.get(card=self.champa, location=self.deck, fake=True)
        self.assertEqual(fake.notes, "Pág. 74 · fila 3 · col 3")  # la posición se va con la copia

    def test_my_order_inside_a_location(self):
        CollectionEntry.objects.filter(location=self.deck, card=self.pr).update(position=1)
        CollectionEntry.objects.filter(location=self.deck, card=self.champa).update(position=2)
        data = self.search(scope="collection", location=self.deck.id, include_fakes=True, ordering="position").data
        self.assertEqual([r["card_number"] for r in data["results"]], ["BT1-005", "BT1-001"])

    def test_reorder(self):
        self.assertEqual(self.post("reorder/", {"location": self.deck.id, "card_ids": [1088, 4]}).status_code, 204)
        data = self.search(scope="collection", location=self.deck.id, include_fakes=True, ordering="position").data
        self.assertEqual([r["id"] for r in data["results"]], [1088, 4])
        self.assertEqual(self.post("reorder/", {"location": self.deck.id, "card_ids": []}).status_code, 400)

    def test_facets_of_an_empty_location(self):
        data = self.client.get("/api/facets/?scope=collection&location=99").data
        self.assertEqual(data["total"], 0)
        self.assertEqual(data["facets"]["color"]["values"], [])

    def test_facets_only_count_owned_cards(self):
        facets = self.client.get("/api/facets/?scope=collection").data
        self.assertEqual(facets["total"], 2)
        self.assertEqual({v["value"]: v["count"] for v in facets["facets"]["color"]["values"]}, {"Red": 2})
        battle = {"op": "and", "children": [{"field": "type", "operator": "in", "value": ["BATTLE"]}]}
        self.assertEqual(self.client.post("/api/facets/", {"scope": "collection", "query": battle}, format="json").data["total"], 1)
        # Las facetas se recalculan en cuanto cambia la colección.
        self.post("adjust/", {"card_id": 7, "delta": 1})
        self.assertEqual(self.client.get("/api/facets/?scope=collection").data["total"], 3)

    def test_order_by_quantity(self):
        self.assertEqual([r["card_number"] for r in self.search(scope="collection", ordering="-quantity").data["results"]],
                         ["BT1-001", "BT1-005"])
        self.assertEqual([r["card_number"] for r in self.search(scope="collection", ordering="quantity").data["results"]],
                         ["BT1-005", "BT1-001"])

    def test_normal_search_has_no_copies(self):
        data = self.search().data
        self.assertEqual(data["count"], 3)
        self.assertNotIn("total_copies", data)

    def test_summary_endpoint(self):
        data = self.client.get("/api/my-collection/").data
        self.assertEqual((data["total_cards"], data["total_copies"]), (2, 5))

    def test_backup_downloads_every_entry_as_compact_json(self):
        response = self.client.get("/api/my-collection/backup/")
        self.assertEqual(response.status_code, 200)
        self.assertRegex(response["Content-Disposition"], r'attachment; filename="mi-coleccion-\d{4}-\d{2}-\d{2}\.json"')
        doc = json.loads(response.content)
        self.assertEqual((doc["format"], doc["version"]), ("dbs-collection", 4))
        self.assertEqual(doc["total_fakes"], 1)
        self.assertIn({"id": 1088, "number": "BT1-005", "name": "Champa PR", "qty": 1, "location": "Mazo rojo", "fake": True}, doc["cards"])
        self.assertEqual(doc["locations"], [
            {"name": "Sin ubicar", "kind": "otro", "cards": 2, "copies": 3},
            {"name": "Caja vacía", "kind": "almacén", "cards": 0, "copies": 0},  # también las vacías
            {"name": "Mazo rojo", "kind": "mazo", "cards": 2, "copies": 2, "fakes": 1, "notes": "funda roja"},
        ])
        self.assertEqual((doc["total_cards"], doc["total_copies"]), (2, 5))
        self.assertEqual(doc["cards"][:2], [
            {"id": 4, "number": "BT1-001", "name": "Champa", "qty": 1, "location": "Mazo rojo", "notes": "titular"},
            {"id": 4, "number": "BT1-001", "name": "Champa", "qty": 2, "location": "Sin ubicar"},
        ])
        # cabecera + una línea por ubicación y por carta + cierres
        self.assertEqual(len(response.content.decode().splitlines()), len(doc["locations"]) + len(doc["cards"]) + 5)

    def test_adjust(self):
        data = self.post("adjust/", {"card_id": 4, "delta": 1}).data
        self.assertEqual((data["card_id"], data["quantity"]), (4, 4))
        self.assertEqual(self.qty(self.champa, self.loose), 3)  # sin ubicación, a «Sin ubicar»
        self.post("adjust/", {"card_id": 7, "delta": 2, "location": self.box.id})
        self.assertEqual(self.qty(self.vados, self.box), 2)
        self.post("adjust/", {"card_id": 7, "delta": -1})  # de la única ubicación con copias
        self.assertEqual(self.qty(self.vados, self.box), 1)
        # Al restar, primero las auténticas; con fake=true, las falsas.
        self.post("adjust/", {"card_id": 1088, "delta": -1, "location": self.deck.id, "fake": True})
        self.assertEqual(self.qty(self.pr, self.deck, fake=True), 0)

    def test_adjust_validation(self):
        self.assertEqual(self.post("adjust/", {"card_id": 4, "delta": 0}).status_code, 400)
        self.assertEqual(self.post("adjust/", {"card_id": 4, "delta": 50}).status_code, 400)
        self.assertEqual(self.post("adjust/", {"card_id": 123456, "delta": 1}).status_code, 400)
        self.assertEqual(self.post("adjust/", {"card_id": 4, "delta": 1, "location": 999}).status_code, 400)

    def test_remove_with_copies_in_several_locations_returns_409_with_them(self):
        CollectionEntry.objects.filter(card=self.champa, location=self.loose).delete()
        CollectionEntry.objects.create(card=self.champa, location=self.box, quantity=1)
        response = self.post("adjust/", {"card_id": 4, "delta": -1})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(sorted(loc["name"] for loc in response.data["locations"]), ["Caja vacía", "Mazo rojo"])

    def test_move_and_note(self):
        data = self.post("move/", {"card_id": 4, "source": self.loose.id, "target": self.deck.id, "quantity": 2}).data
        self.assertEqual([(loc["name"], loc["quantity"]) for loc in data["locations"]], [("Mazo rojo", 3)])
        self.assertEqual(self.post("move/", {"card_id": 4, "source": self.loose.id, "target": self.deck.id,
                                             "quantity": 1}).status_code, 400)  # ya no quedan
        self.post("note/", {"card_id": 4, "location": self.deck.id, "notes": "pág. 3"})
        self.assertEqual(CollectionEntry.objects.get(card=self.champa, location=self.deck).notes, "pág. 3")
        self.assertEqual(self.post("note/", {"card_id": 7, "location": self.deck.id, "notes": "x"}).status_code, 404)

    def test_each_deck_shows_its_awakened_leader(self):
        Card.objects.filter(id=4).update(back_name="Champa, Fighting for Fun", back_image_url="https://x/BT1-001_b.png")
        z = Card.objects.create(id=50, card_number="EX21-19", name="Z Champa", card_type="Z-LEADER", colors=["Red"])
        CollectionEntry.objects.create(card=z, location=self.deck, quantity=1)
        data = {loc["name"]: loc for loc in self.client.get("/api/my-collection/locations/").data}
        self.assertIsNone(data["Sin ubicar"]["leader"])  # no es un mazo
        self.assertEqual(data["Mazo rojo"]["leader"], {"id": 4, "card_number": "BT1-001", "name": "Champa, Fighting for Fun",
                                                       "image": "https://x/BT1-001_b.png", "awakened": True,
                                                       "colors": ["Red"]})
        self.assertEqual((data["Mazo rojo"]["copies"], data["Mazo rojo"]["fakes"]), (3, 1))
        self.assertTrue(data["Mazo rojo"]["uid"])

    def test_locations_crud(self):
        r = self.client.post("/api/my-collection/locations/", {"name": "Archivador 1", "kind": "binder", "x": 1}, format="json")
        self.assertEqual(r.status_code, 201)
        pk = r.data["id"]
        self.assertEqual(self.client.post("/api/my-collection/locations/", {"name": "Archivador 1"}, format="json").status_code, 400)
        r = self.client.patch(f"/api/my-collection/locations/{pk}/", {"name": "Archivador azul"}, format="json")
        self.assertEqual((r.data["name"], r.data["kind"]), ("Archivador azul", "binder"))
        # Al borrarla, sus copias vuelven a «Sin ubicar».
        self.post("adjust/", {"card_id": 7, "delta": 2, "location": pk})
        self.assertEqual(self.client.delete(f"/api/my-collection/locations/{pk}/").status_code, 204)
        self.assertEqual(self.qty(self.vados, self.loose), 2)
        self.assertEqual(self.client.delete(f"/api/my-collection/locations/{self.loose.id}/").status_code, 400)
        self.assertEqual(self.client.delete("/api/my-collection/locations/999/").status_code, 404)


class SearchShowsOwnedCopiesTests(TestCase):
    """En el buscador (todo el catálogo), cada carta trae tus copias para la insignia y la ficha."""

    def setUp(self):
        self.champa = Card.objects.create(id=4, card_number="BT1-001", name="Champa", card_type="LEADER", colors=["Red"])
        self.vados = Card.objects.create(id=7, card_number="BT1-008", name="Vados", card_type="BATTLE", colors=["Blue"])
        self.deck = Location.objects.create(name="Mazo rojo", kind="deck")
        CollectionEntry.objects.create(card=self.champa, location=Location.default(), quantity=2)
        CollectionEntry.objects.create(card=self.champa, location=self.deck, quantity=1, fake=True)
        self.client = APIClient()

    def test_owned_cards_carry_their_copies(self):
        results = {r["id"]: r for r in self.client.post("/api/cards/search/", {}, format="json").data["results"]}
        self.assertEqual(results[4]["quantity"], 2)  # auténticas
        self.assertEqual(results[4]["total_quantity"], 3)
        self.assertEqual(results[4]["fakes"], 1)
        self.assertEqual(sorted(loc["name"] for loc in results[4]["locations"]), ["Mazo rojo", "Sin ubicar"])
        self.assertNotIn("quantity", results[7])  # no la tienes
        self.assertEqual(len(results), 2)  # el buscador sigue mostrando todo el catálogo
