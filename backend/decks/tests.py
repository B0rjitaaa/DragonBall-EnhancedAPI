from django.test import TestCase
from rest_framework.test import APIClient

from cards.models import Card
from collection.models import CollectionEntry, Location


class DeckListsTests(TestCase):
    """Versiones de lista de un mazo, side deck y partidas."""

    def setUp(self):
        self.client = APIClient()
        self.deck = Location.objects.create(name="Mazo Cell", kind="deck")
        self.leader = Card.objects.create(id=1, card_number="EX20-01", name="Cell", card_type="LEADER")
        self.a = Card.objects.create(id=2, card_number="EX20-02", name="Cell Jr.", card_type="BATTLE")
        self.b = Card.objects.create(id=3, card_number="EX20-03", name="Android 17", card_type="BATTLE")
        self.z = Card.objects.create(id=4, card_number="BT21-070", name="Z Cell", card_type="Z-BATTLE")
        for card, n in ((self.leader, 1), (self.a, 4), (self.z, 1)):
            CollectionEntry.objects.create(card=card, location=self.deck, quantity=n)
        CollectionEntry.objects.create(card=self.a, location=self.deck, quantity=1, fake=True)  # las falsas cuentan

    def deck_data(self):
        return self.client.get(f"/api/my-collection/decks/{self.deck.id}/").data

    def match(self, **body):
        data = {"played_on": "2026-10-20", "result": "win", "opponent_leader_bandai_id": 99,
                "opponent_leader_name": "Son Goku", "opponent_name": "Pepe", **body}
        return self.client.post(f"/api/my-collection/decks/{self.deck.id}/matches/", data, format="json")

    def test_current_list_by_section_counts_fakes(self):
        current = {(c["bandai_id"], c["section"]): c["quantity"] for c in self.deck_data()["current"]}
        self.assertEqual(current, {(1, "main"): 1, (2, "main"): 5, (4, "z"): 1})

    def test_responses_include_catalog_data_of_their_cards(self):
        data = self.deck_data()
        self.assertEqual(sorted(data["catalog"]), [1, 2, 4])
        self.assertEqual(data["catalog"][4]["name"], "Z Cell")

    def test_side_deck(self):
        r = self.client.post(f"/api/my-collection/decks/{self.deck.id}/side/", {"bandai_id": 2, "quantity": 9}, format="json")
        self.assertEqual(r.data["side"], 5)  # no más de las que hay
        self.client.post(f"/api/my-collection/decks/{self.deck.id}/side/", {"bandai_id": 2, "quantity": 2}, format="json")
        current = {(c["bandai_id"], c["section"]): c["quantity"] for c in self.deck_data()["current"]}
        self.assertEqual((current[(2, "main")], current[(2, "side")]), (3, 2))

    def test_versions_and_changes(self):
        v1 = self.client.post(f"/api/my-collection/decks/{self.deck.id}/versions/", {"name": "Pre-regional"}, format="json").data
        self.assertEqual((v1["number"], v1["name"], v1["automatic"]), (1, "Pre-regional", False))
        CollectionEntry.objects.filter(card=self.a, fake=False).update(quantity=2)  # quito 2 Cell Jr.
        CollectionEntry.objects.create(card=self.b, location=self.deck, quantity=3)  # entran 3 Android 17
        self.assertEqual(
            sorted((c["bandai_id"], c["delta"]) for c in self.deck_data()["changes"]), [(2, -2), (3, 3)]
        )
        v2 = self.client.post(f"/api/my-collection/decks/{self.deck.id}/versions/", {}, format="json").data
        detail = self.client.get(f"/api/my-collection/deck-versions/{v2['id']}/").data
        self.assertEqual((detail["number"], detail["previous"]), (2, 1))
        self.assertEqual(sorted((c["bandai_id"], c["delta"]) for c in detail["changes"]), [(2, -2), (3, 3)])
        # La versión antigua no cambia.
        old = self.client.get(f"/api/my-collection/deck-versions/{v1['id']}/").data
        self.assertIn({"bandai_id": 2, "section": "main", "quantity": 5}, old["cards"])

    def test_matches_use_the_principal_list(self):
        m1 = self.match().data  # sin listas: se guarda la de la caja (automática) y pasa a principal
        m2 = self.match(result="loss", went_first=True, score="1-2", event="Regional Madrid").data
        self.assertEqual(m1["version"], m2["version"])
        CollectionEntry.objects.create(card=self.b, location=self.deck, quantity=1)
        m3 = self.match(opponent_leader_bandai_id=77, opponent_leader_name="Vegeta").data
        self.assertEqual(m3["version"], m1["version"])  # se juega con la principal aunque la caja cambie
        data = self.deck_data()
        self.assertEqual([(v["number"], v["automatic"], v["principal"]) for v in data["versions"]], [(1, True, True)])
        self.assertEqual(data["principal"], m1["version"])
        self.assertEqual([(c["bandai_id"], c["delta"]) for c in data["changes"]], [(3, 1)])
        self.assertEqual((data["record"]["wins"], data["record"]["losses"], data["record"]["played"]), (2, 1, 3))
        goku = next(r for r in data["by_leader"] if r["leader_name"] == "Son Goku")
        self.assertEqual(len(data["matches"]), data["record"]["played"])
        self.assertTrue(all("version_number" in m for m in data["matches"]))
        self.assertEqual((goku["wins"], goku["losses"], goku["win_rate"]), (1, 1, 0.5))

    def test_match_against_an_old_version_and_editing(self):
        v1 = self.client.post(f"/api/my-collection/decks/{self.deck.id}/versions/", {}, format="json").data
        CollectionEntry.objects.create(card=self.b, location=self.deck, quantity=1)
        m = self.match(version=v1["id"]).data
        self.assertEqual(m["version"], v1["id"])
        self.client.patch(f"/api/my-collection/matches/{m['id']}/", {"result": "draw"}, format="json")
        self.assertEqual(self.client.get(f"/api/my-collection/deck-versions/{v1['id']}/").data["record"]["draws"], 1)
        self.assertEqual(self.client.delete(f"/api/my-collection/deck-versions/{v1['id']}/").status_code, 400)  # tiene partidas
        self.client.delete(f"/api/my-collection/matches/{m['id']}/")
        self.assertEqual(self.client.delete(f"/api/my-collection/deck-versions/{v1['id']}/").status_code, 204)

    def test_only_decks(self):
        box = Location.objects.create(name="Caja", kind="storage")
        self.assertEqual(self.client.get(f"/api/my-collection/decks/{box.id}/").status_code, 404)

    def test_a_deck_with_matches_cannot_be_deleted(self):
        self.match()
        self.assertEqual(self.client.delete(f"/api/my-collection/locations/{self.deck.id}/").status_code, 400)


class RestoreVersionTests(TestCase):
    """Hacer principal una versión: las copias se mueven de verdad."""

    def setUp(self):
        self.client = APIClient()
        self.deck = Location.objects.create(name="Mazo Cell", kind="deck")
        self.binder = Location.objects.create(name="Archivador", kind="binder")
        self.other_deck = Location.objects.create(name="Otro mazo", kind="deck")
        self.loose = Location.default()
        self.a = Card.objects.create(id=2, card_number="EX20-02", name="Cell Jr.", card_type="BATTLE")
        self.b = Card.objects.create(id=3, card_number="EX20-03", name="Android 17", card_type="BATTLE")
        CollectionEntry.objects.create(card=self.a, location=self.deck, quantity=4)
        CollectionEntry.objects.create(card=self.b, location=self.deck, quantity=3)
        self.client.post(f"/api/my-collection/decks/{self.deck.id}/side/", {"bandai_id": 3, "quantity": 1}, format="json")
        self.v1 = self.client.post(f"/api/my-collection/decks/{self.deck.id}/versions/", {}, format="json").data
        # Después: salen 2 Cell Jr. (una era falsa) y todos los Android 17 al archivador.
        CollectionEntry.objects.filter(card=self.a, location=self.deck).update(quantity=1)
        CollectionEntry.objects.create(card=self.a, location=self.deck, quantity=1, fake=True)
        CollectionEntry.objects.filter(card=self.b, location=self.deck).update(location=self.binder)
        CollectionEntry.objects.create(card=self.a, location=self.loose, quantity=1)
        CollectionEntry.objects.create(card=self.a, location=self.other_deck, quantity=2)

    def qty(self, card, loc, fake=None):
        q = CollectionEntry.objects.filter(card=card, location=loc)
        if fake is not None:
            q = q.filter(fake=fake)
        return sum(q.values_list("quantity", flat=True))

    def test_plan(self):
        plan = self.client.get(f"/api/my-collection/deck-versions/{self.v1['id']}/restore/").data
        self.assertEqual(plan["outgoing"], [])
        incoming = {r["bandai_id"]: r for r in plan["incoming"]}
        self.assertEqual((incoming[2]["quantity"], incoming[3]["quantity"]), (2, 3))
        # Primero «Sin ubicar», el otro mazo el último.
        self.assertEqual([s["name"] for s in incoming[2]["sources"]], ["Sin ubicar", "Otro mazo"])

    def test_restore_moves_copies_and_side(self):
        r = self.client.post(f"/api/my-collection/deck-versions/{self.v1['id']}/restore/", {}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["missing"], [])
        self.assertEqual(self.qty(self.a, self.deck), 4)
        self.assertEqual(self.qty(self.a, self.loose), 0)  # la de «Sin ubicar» primero
        self.assertEqual(self.qty(self.a, self.other_deck), 1)
        self.assertEqual((self.qty(self.b, self.deck), self.qty(self.b, self.binder)), (3, 0))
        data = self.client.get(f"/api/my-collection/decks/{self.deck.id}/").data
        self.assertEqual(data["changes"], [])  # la lista actual es la de v1, side incluido
        self.assertIn({"bandai_id": 3, "section": "side", "quantity": 1}, data["current"])

    def test_outgoing_go_to_chosen_place_fakes_first(self):
        v2 = self.client.post(f"/api/my-collection/decks/{self.deck.id}/versions/", {}, format="json").data  # 1 + 1 falsa
        self.client.post(f"/api/my-collection/deck-versions/{self.v1['id']}/restore/", {}, format="json")
        r = self.client.post(f"/api/my-collection/deck-versions/{v2['id']}/restore/",
                             {"targets": {"3": self.binder.id}, "default_target": self.loose.id}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(self.qty(self.b, self.binder), 3)
        # Sobran 2 Cell Jr.: sale antes la falsa, así el mazo se queda con las auténticas.
        self.assertEqual((self.qty(self.a, self.deck, fake=False), self.qty(self.a, self.deck, fake=True)), (2, 0))
        self.assertEqual((self.qty(self.a, self.loose, fake=False), self.qty(self.a, self.loose, fake=True)), (1, 1))

    def test_missing_copies_are_reported(self):
        CollectionEntry.objects.filter(card=self.a).exclude(location=self.deck).delete()
        r = self.client.post(f"/api/my-collection/deck-versions/{self.v1['id']}/restore/",
                             {"sources": {"3": self.binder.id}}, format="json")
        self.assertEqual(r.data["missing"], [{"bandai_id": 2, "quantity": 2}])
        self.assertEqual(self.qty(self.b, self.deck), 3)


class EditedListTests(TestCase):
    """Listas creadas desde el editor: no mueven copias hasta hacerlas principales."""

    def setUp(self):
        self.client = APIClient()
        self.deck = Location.objects.create(name="Mazo Cell", kind="deck")
        self.a = Card.objects.create(id=2, card_number="EX20-02", name="Cell Jr.", card_type="BATTLE")
        self.b = Card.objects.create(id=3, card_number="EX20-03", name="Android 17", card_type="BATTLE")
        self.z = Card.objects.create(id=4, card_number="BT21-070", name="Z Cell", card_type="Z-BATTLE")
        CollectionEntry.objects.create(card=self.a, location=self.deck, quantity=4)
        CollectionEntry.objects.create(card=self.b, location=Location.default(), quantity=2)

    def save(self, cards, **body):
        return self.client.post(f"/api/my-collection/decks/{self.deck.id}/versions/", {"cards": cards, **body}, format="json").data

    def test_saving_the_box_list_makes_it_principal(self):
        v = self.save([{"bandai_id": 2, "section": "main", "quantity": 4}])
        self.assertTrue(v["principal"])

    def test_edited_list_is_saved_without_moving_copies(self):
        self.save([{"bandai_id": 2, "section": "main", "quantity": 4}])
        cards = [{"bandai_id": 2, "section": "main", "quantity": 3}, {"bandai_id": 3, "section": "side", "quantity": 2},
                 {"bandai_id": 4, "section": "main", "quantity": 1}]  # Z Cell va al Z Deck por su tipo
        plan = self.client.post(f"/api/my-collection/decks/{self.deck.id}/plan/", {"cards": cards}, format="json").data
        self.assertEqual(plan["outgoing"], [{"bandai_id": 2, "quantity": 1, "fakes": 0}])
        incoming = {r["bandai_id"]: r for r in plan["incoming"]}
        self.assertEqual((incoming[3]["missing"], incoming[4]["missing"]), (0, 1))
        v2 = self.save(cards, name="Más control")
        self.assertFalse(v2["principal"])
        detail = self.client.get(f"/api/my-collection/deck-versions/{v2['id']}/").data
        self.assertIn({"bandai_id": 4, "section": "z", "quantity": 1}, detail["cards"])
        self.assertEqual(CollectionEntry.objects.get(card=self.a, location=self.deck).quantity, 4)  # no se mueve nada
        # Hacerla principal sí mueve las copias, y las partidas se anotan con ella.
        self.client.post(f"/api/my-collection/deck-versions/{v2['id']}/restore/", {}, format="json")
        data = self.client.get(f"/api/my-collection/decks/{self.deck.id}/").data
        self.assertEqual(data["principal"], v2["id"])
        m = self.client.post(f"/api/my-collection/decks/{self.deck.id}/matches/",
                             {"played_on": "2026-10-26", "result": "win"}, format="json").data
        self.assertEqual(m["version"], v2["id"])


class DeckHistoryTests(TestCase):
    """Pasar un mazo al histórico: guarda su lista, saca sus copias a «Sin ubicar» y lo marca."""

    def setUp(self):
        self.client = APIClient()
        self.deck = Location.objects.create(name="Mazo Cell", kind="deck")
        self.leader = Card.objects.create(id=1, card_number="EX20-01", name="Cell", card_type="LEADER", colors=["Green"])
        self.a = Card.objects.create(id=2, card_number="EX20-02", name="Cell Jr.", card_type="BATTLE",
                                     legality="banned")
        CollectionEntry.objects.create(card=self.leader, location=self.deck, quantity=1)
        CollectionEntry.objects.create(card=self.a, location=self.deck, quantity=3, notes="caja roja")
        CollectionEntry.objects.create(card=self.a, location=self.deck, quantity=1, fake=True)
        self.url = f"/api/my-collection/decks/{self.deck.id}/to-history/"

    def listing(self):
        return {loc["name"]: loc for loc in self.client.get("/api/my-collection/locations/").data}

    def test_preview_does_not_move_anything(self):
        r = self.client.get(self.url)
        self.assertEqual([(c["card_number"], c["quantity"], c["fake"]) for c in r.data["cards"]],
                         [("EX20-01", 1, False), ("EX20-02", 3, False), ("EX20-02", 1, True)])
        self.assertEqual(CollectionEntry.objects.filter(location=self.deck).count(), 3)

    def test_move_to_history(self):
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(sum(c["quantity"] for c in r.data["cards"]), 5)
        self.assertFalse(CollectionEntry.objects.filter(location=self.deck).exists())
        unplaced = Location.default()
        moved = {(e.card_id, e.fake): (e.quantity, e.notes) for e in CollectionEntry.objects.filter(location=unplaced)}
        self.assertEqual(moved, {(1, False): (1, ""), (2, False): (3, "caja roja"), (2, True): (1, "")})
        self.deck.refresh_from_db()
        self.assertEqual(self.deck.status, "parked")
        self.assertIsNotNone(self.deck.parked_at)
        version = self.deck.deck_versions.get()
        self.assertTrue(version.automatic)
        # En la lista sigue con su líder y el tamaño de su última lista, aunque la caja esté vacía.
        deck = self.listing()["Mazo Cell"]
        self.assertEqual((deck["copies"], deck["last_list"], deck["leader"]["id"]), (0, 5, 1))
        self.assertEqual(self.client.post(self.url).status_code, 400)  # ya está en el histórico

    def back_url(self):
        return f"/api/my-collection/decks/{self.deck.id}/back-in-use/"

    def test_status_only_changes_through_its_actions(self):
        for value in ("parked", "active"):  # PATCH no cambia el estado en ninguna dirección
            r = self.client.patch(f"/api/my-collection/locations/{self.deck.id}/", {"status": value}, format="json")
            self.assertEqual(r.status_code, 400)
            self.client.post(self.url)
        self.assertEqual(self.client.post(self.back_url()).status_code, 200)
        self.assertEqual(self.client.post(self.back_url()).status_code, 400)  # ya está en uso

    def test_back_in_use_brings_its_leader(self):
        self.client.post(self.url)
        # Una copia auténtica del líder en un archivador va antes que una falsa en «Sin ubicar».
        binder = Location.objects.create(name="Archivador", kind="binder")
        CollectionEntry.objects.filter(card=self.leader).update(location=binder)
        CollectionEntry.objects.create(card=self.leader, location=Location.default(), quantity=1, fake=True)
        r = self.client.post(self.back_url())
        self.assertEqual((r.data["leader"]["card_number"], r.data["leader"]["from"], r.data["leader"]["fake"]),
                         ("EX20-01", "Archivador", False))
        self.deck.refresh_from_db()
        self.assertEqual((self.deck.status, self.deck.parked_at), ("active", None))
        in_deck = {(e.card_id, e.fake): e.quantity for e in CollectionEntry.objects.filter(location=self.deck)}
        self.assertEqual(in_deck, {(1, False): 1})  # solo el líder; lo demás, restaurando la versión

    def test_back_in_use_without_leader_copies(self):
        self.client.post(self.url)
        CollectionEntry.objects.filter(card=self.leader).delete()
        r = self.client.post(self.back_url())
        self.assertIsNone(r.data["leader"])
        # Aun sin tenerlo, el mazo enseña el líder de su última lista.
        self.assertEqual(self.listing()["Mazo Cell"]["leader"]["id"], 1)

    def test_status_log(self):
        self.assertEqual(self.listing()["Mazo Cell"]["status_log"], [])
        self.client.post(self.url)
        self.client.post(self.back_url())
        self.client.post(self.url)  # solo vuelve a salir el líder
        log = self.listing()["Mazo Cell"]["status_log"]
        self.assertEqual([(e["status"], e["copies"]) for e in log], [("parked", 1), ("active", 0), ("parked", 5)])

    def test_deck_issues_and_leader_colors(self):
        deck = self.listing()["Mazo Cell"]
        self.assertEqual(deck["issues"], {"banned": ["EX20-02"], "limited": []})  # las falsas no cuentan
        self.assertEqual(deck["leader"]["colors"], ["Green"])
        self.assertEqual(deck["status"], "active")
