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
        self.assertEqual([s["name"] for s in incoming[2]["sources"]], ["Unsorted", "Otro mazo"])

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


class DeckImportTests(TestCase):
    """Importar un mazo (enlace o texto): qué tienes libre, qué está en otros mazos y qué falta; crearlo."""

    def setUp(self):
        from decks.models import SideCard

        self.client, self.Side = APIClient(), SideCard
        self.leader = Card.objects.create(id=1, card_number="EX20-01", name="Cell", card_type="LEADER")
        self.a = Card.objects.create(id=2, card_number="BT29-86", name="Goku Black", card_type="BATTLE")
        self.a_alt = Card.objects.create(id=3, card_number="BT29-86", name="Goku Black", card_type="BATTLE")  # alt art
        self.b = Card.objects.create(id=4, card_number="EX20-03", name="Android 17", card_type="BATTLE")
        self.z = Card.objects.create(id=5, card_number="BT21-070", name="Z Cell", card_type="Z-BATTLE")
        self.box = Location.objects.create(name="Caja 1", kind="storage")
        self.other = Location.objects.create(name="Mazo viejo", kind="deck")
        self.third = Location.objects.create(name="Mazo intocable", kind="deck")
        CollectionEntry.objects.create(card=self.leader, location=self.box, quantity=1, notes="P. 3 · row 1 · col 2")
        CollectionEntry.objects.create(card=self.a, location=self.box, quantity=1)
        CollectionEntry.objects.create(card=self.a_alt, location=self.box, quantity=1)  # otra impresión: cuenta
        CollectionEntry.objects.create(card=self.a, location=self.box, quantity=2, fake=True)  # falsas: no cuentan
        CollectionEntry.objects.create(card=self.a, location=self.other, quantity=2)
        CollectionEntry.objects.create(card=self.b, location=self.third, quantity=1)
        SideCard.objects.create(deck=self.other, card=self.a, quantity=2)
        self.text = "_____Leader_____\nCell [EX20-01]\n_____Main Deck_____\n4 Goku Black [BT29-086]\n2x EX20-03\n" \
                    "_____Z Deck_____\nBT21-70 x1\n## Side Deck\n1 BT29-086"

    def preview(self, source):
        return self.client.post("/api/my-collection/decks/import/preview/", {"source": source}, format="json")

    def test_text_list_preview(self):
        data = self.preview(self.text).data
        rows = {r["number"]: r for r in data["rows"]}
        # BT29-086 = BT29-86; 4 en el main + 1 en el side = 5: 2 libres (dos impresiones), 2 en otro mazo, 1 falta.
        goku = rows["BT29-86"]
        self.assertEqual((goku["sections"], goku["free"], goku["missing"]), ({"main": 4, "side": 1}, 2, 1))
        self.assertEqual(goku["in_use"], [{"deck_id": self.other.id, "deck": "Mazo viejo", "quantity": 2}])
        self.assertEqual((rows["EX20-03"]["in_use"][0]["deck"], rows["EX20-03"]["missing"]), ("Mazo intocable", 1))
        self.assertEqual(rows["BT21-070"]["missing"], 1)
        self.assertTrue(data["has_leader"])
        self.assertEqual(data["totals"], {"cards": 9, "in_deck": 0, "free": 3, "in_use": 3, "missing": 3, "leaving": 0})
        self.assertEqual((data["existing_decks"], data["target"], data["leaving"]), ([], None, []))
        self.assertIn(str(self.a.id), {str(k) for k in data["catalog"]})
        self.assertEqual(goku["from"], [{"location": "Caja 1", "quantity": 2}])

    def test_create_takes_free_copies_and_only_accepted_decks(self):
        lines = self.preview(self.text).data["lines"]
        body = {"lines": lines, "name": "Goku Black", "source": "text", "take_from": [self.other.id]}
        response = self.client.post("/api/my-collection/decks/import/", body, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        data = response.data
        new = Location.objects.get(name="Goku Black")
        self.assertEqual(new.kind, "deck")
        have = {(e.card_id, e.fake): e.quantity for e in CollectionEntry.objects.filter(location=new)}
        self.assertEqual(have, {(1, False): 1, (2, False): 3, (3, False): 1})  # leader, 1+2 Goku, 1 alt
        self.assertFalse(CollectionEntry.objects.filter(location=self.other).exists())  # aceptado: se vacía
        self.assertTrue(CollectionEntry.objects.filter(location=self.third, card=self.b).exists())  # no aceptado
        self.assertTrue(CollectionEntry.objects.filter(location=self.box, card=self.a, fake=True).exists())
        self.assertEqual((data["moved"], data["missing"]), (5, 4))
        # El mazo nuevo guarda la lista completa (también lo que falta) como principal; el side, aparte.
        from decks.services import principal_version, version_list

        listing = version_list(principal_version(new))
        self.assertEqual(sum(n for (_c, s), n in listing.items() if s == "side"), 1)
        self.assertEqual(sum(listing.values()), 9)
        # Las 4 copias que hay de Goku van al Main Deck: la del side falta, así que en la caja no hay side.
        self.assertFalse(self.Side.objects.filter(deck=new).exists())
        # El mazo del que salen cartas guarda una versión nueva con lo que le queda (y su side se ajusta).
        self.assertEqual(data["decks_changed"], [{"deck_id": self.other.id, "deck": "Mazo viejo", "copies": 2, "version": 1}])
        version = principal_version(self.other)
        self.assertEqual((version.name, version_list(version)), ("Gave cards to “Goku Black”", {}))
        self.assertFalse(self.Side.objects.filter(deck=self.other).exists())
        # Lista de recogida: primero la caja (libres), luego el otro mazo; con las notas de posición.
        picks = data["pick_list"]
        self.assertEqual([g["location"] for g in picks], ["Caja 1", "Mazo viejo"])
        box = {(c["bandai_id"], c["quantity"]) for c in picks[0]["cards"]}
        self.assertEqual(box, {(1, 1), (2, 1), (3, 1)})
        self.assertEqual(picks[0]["cards"][0]["notes"], ["P. 3 · row 1 · col 2"])
        self.assertEqual(picks[1]["cards"], [{"bandai_id": 2, "number": "BT29-86", "name": "Goku Black", "rarity": "",
                                             "quantity": 2, "position": 1, "notes": []}])

    def test_pick_list_is_saved_with_the_deck(self):
        lines = self.preview(self.text).data["lines"]
        body = {"lines": lines, "name": "Goku Black", "take_from": [self.other.id]}
        deck_id = self.client.post("/api/my-collection/decks/import/", body, format="json").data["deck"]["id"]
        url = f"/api/my-collection/decks/{deck_id}/pick-list/"
        data = self.client.get(url).data
        self.assertEqual([g["location"] for g in data["groups"]], ["Caja 1", "Mazo viejo"])
        self.assertIn(1, data["catalog"])
        self.assertEqual(self.client.get(f"/api/my-collection/decks/{deck_id}/").data["pick_list"], {"total": 4, "done": 0})
        key = f"{self.box.id}-1"
        saved = self.client.patch(url, {"done": [key, key, "999-999"]}, format="json").data
        self.assertEqual(saved["done"], [key])  # sin repetidas ni claves que no existen
        self.assertEqual(self.client.get(f"/api/my-collection/decks/{deck_id}/").data["pick_list"], {"total": 4, "done": 1})
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertIsNone(self.client.get(f"/api/my-collection/decks/{deck_id}/").data["pick_list"])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_leader_you_already_have_adds_a_list_to_that_deck(self):
        from decks.services import principal_version, version_list

        cell = Location.objects.create(name="Cell de siempre", kind="deck")
        extra = Card.objects.create(id=9, card_number="BT1-001", name="Champa", card_type="BATTLE")
        CollectionEntry.objects.create(card=self.leader, location=cell, quantity=1, notes="caja azul")
        CollectionEntry.objects.create(card=self.z, location=cell, quantity=1)
        CollectionEntry.objects.create(card=extra, location=cell, quantity=3)  # no está en la lista nueva
        self.Side.objects.create(deck=cell, card=extra, quantity=1)
        data = self.preview(self.text).data
        self.assertEqual(data["existing_decks"], [{"id": cell.id, "name": "Cell de siempre"}])
        body = {"lines": data["lines"], "source": "text", "target": cell.id}
        data = self.client.post("/api/my-collection/decks/import/preview/", body, format="json").data
        self.assertEqual(data["target"], {"id": cell.id, "name": "Cell de siempre"})
        rows = {r["number"]: r for r in data["rows"]}
        self.assertEqual((rows["EX20-01"]["in_deck"], rows["EX20-01"]["free"]), (1, 0))  # el Leader ya está en el mazo
        self.assertEqual((rows["BT21-070"]["in_deck"], rows["BT21-070"]["missing"]), (1, 0))
        self.assertEqual(data["leaving"], [{"bandai_id": 9, "number": "BT1-001", "name": "Champa", "quantity": 3, "fake": False}])
        self.assertEqual((data["totals"]["in_deck"], data["totals"]["leaving"]), (2, 3))

        response = self.client.post("/api/my-collection/decks/import/", {**body, "take_from": []}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        result = response.data
        self.assertEqual((result["deck"]["id"], result["created"], result["removed"]), (cell.id, False, 3))
        self.assertFalse(Location.objects.filter(name="text").exists())
        self.assertEqual(Location.objects.filter(kind="deck").count(), 3)  # no se crea otro mazo
        # Lo que no está en la lista nueva, a «Unsorted»; lo que estaba y sigue, se queda.
        unsorted = Location.default()
        self.assertEqual(CollectionEntry.objects.get(location=unsorted, card=extra).quantity, 3)
        have = {e.card_id: e.quantity for e in CollectionEntry.objects.filter(location=cell)}
        self.assertEqual(have, {1: 1, 5: 1, 2: 1, 3: 1})  # Leader y Z de antes + 2 Goku libres (dos impresiones)
        self.assertFalse(self.Side.objects.filter(deck=cell, card=extra).exists())
        version = principal_version(cell)
        self.assertEqual((version.number, version.name), (1, "Imported from a text list"))
        self.assertEqual(sum(version_list(version).values()), 9)
        # Lista de recogida: lo que entra (de la caja) y lo que hay que sacar del mazo.
        groups = result["pick_list"]
        self.assertEqual(groups[-1]["kind"], "out")
        self.assertEqual([(c["bandai_id"], c["quantity"]) for c in groups[-1]["cards"]], [(9, 3)])
        self.assertEqual(groups[0]["location"], "Caja 1")

    def test_missing_side_copy_does_not_take_one_from_the_main_deck(self):
        from decks.services import current_list, principal_version, version_list

        # 3 en el Main Deck y 1 en el Side Deck, y solo hay 3: las 3 van al Main Deck y falta la del Side Deck.
        CollectionEntry.objects.create(card=self.b, location=self.box, quantity=3)
        text = "1 EX20-01\n3 EX20-03\nSide Deck\n1 EX20-03"
        lines = self.preview(text).data["lines"]
        body = {"lines": lines, "name": "Sin side", "take_from": []}
        data = self.client.post("/api/my-collection/decks/import/", body, format="json").data
        self.assertEqual((data["moved"], data["missing"]), (4, 1))
        new = Location.objects.get(name="Sin side")
        self.assertEqual(current_list(new), {(1, "main"): 1, (4, "main"): 3})  # la caja: nada en el side
        self.assertFalse(self.Side.objects.filter(deck=new).exists())
        self.assertEqual(version_list(principal_version(new)), {(1, "main"): 1, (4, "main"): 3, (4, "side"): 1})

    def test_side_copies_you_have_go_to_the_side_deck(self):
        from decks.services import current_list

        CollectionEntry.objects.create(card=self.b, location=self.box, quantity=3)
        lines = self.preview("1 EX20-01\n1 EX20-03\nSide Deck\n2 EX20-03").data["lines"]
        body = {"lines": lines, "name": "Con side", "take_from": []}
        data = self.client.post("/api/my-collection/decks/import/", body, format="json").data
        self.assertEqual(data["missing"], 0)
        self.assertEqual(current_list(Location.objects.get(name="Con side")), {(1, "main"): 1, (4, "main"): 1, (4, "side"): 2})

    def test_name_must_be_new(self):
        lines = self.preview(self.text).data["lines"]
        body = {"lines": lines, "name": "caja 1", "take_from": []}
        response = self.client.post("/api/my-collection/decks/import/", body, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("already", response.data["detail"])

    def test_leader_detected_without_section_and_unknown_numbers(self):
        data = self.preview("1 EX20-01\n4 BT29-86\n3 ZZ9-999").data
        self.assertTrue(data["has_leader"])
        self.assertEqual(data["unknown"], ["ZZ9-999"])

    def test_time_chamber_link(self):
        data = self.preview("https://time-chamber.net/decks/import?leader=EX20-01&main=BT29-86x2&z=BT21-070x1&side=EX20-03x1").data
        self.assertEqual(data["source"], "timechamber")
        self.assertEqual(data["totals"]["cards"], 5)

    def test_unknown_site_asks_for_text(self):
        response = self.preview("https://example.com/deck/1")
        self.assertEqual(response.status_code, 400)
        self.assertIn("paste the list as text", response.data["detail"])

    def test_deckplanet_and_topdeckdiffusion_pages(self):
        from unittest import mock

        deck_data = {"deck_name": "Cell", "deck_leader": {"card_number": "EX20-01"},
                     "deck_cards": [{"zone": "main", "amount_in_deck": 3, "card_id": {"card_number": "BT29-086"}},
                                    {"zone": "side", "amount_in_deck": 1, "card_id": {"card_number": "EX20-03"}}],
                     "z_deck_cards": [{"zone": "z", "amount_in_deck": 1, "card_id": {"card_number": "BT21-070"}}]}
        payload = '1:["$","x",null,{"deckData":' + __import__("json").dumps(deck_data) + "}]"
        dp_page = "<script>self.__next_f.push([1," + __import__("json").dumps(payload) + "])</script>"
        tdd_data = {"leaders": [{"qty": 1, "number": "EX20-01"}, {"qty": 1, "number": "EX20-01"}],
                    "main": [{"qty": 3, "number": "BT29-086"}], "zdeck": [{"qty": 1, "number": "BT21-070"}],
                    "side": [{"qty": 1, "number": "EX20-03"}]}
        tdd_page = '<h1 class="tdd-title">Regio Lille &amp; co</h1><script id="export-deck-data" type="application/json">' \
                   + __import__("json").dumps(tdd_data) + "</script>"
        for url, page, name in (("https://www.dbs-deckplanet.com/es/dbs_masters/deck/abc", dp_page, "Cell"),
                                ("https://topdeckdiffusion.com/decks/xyz", tdd_page, "Regio Lille & co")):
            with mock.patch("decks.importer._fetch", return_value=page):
                data = self.preview(url).data
            self.assertEqual((data["name"], data["totals"]["cards"], data["has_leader"]), (name, 6, True), url)
