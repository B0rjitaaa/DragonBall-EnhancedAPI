from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from cards import changes
from cards.importer import upsert_cards
from cards.models import CardChange, Legality


def raw(id, number, name, text="", power="10000", image="a"):
    return {"id": id, "card_number": number, "card_name": name, "card_text": text,
            "image_url": f"https://e/{image}.png", "card_set": "Set",
            "card_config": [{"config_name": "Type", "value": "BATTLE"}, {"config_name": "Power", "value": power}]}


class CardChangesTests(TestCase):
    def setUp(self):
        upsert_cards([raw(10, "BT1-030", "Son Goku", "Draw 1."), raw(11, "BT10-002", "Vegeta")])

    def sync(self, items, catalog_was_empty=False):
        ids = [i["id"] for i in items]
        before = changes.snapshot_cards(ids)
        upsert_cards(items)
        return changes.record_card_changes(before, ids, catalog_was_empty=catalog_was_empty)

    def test_detects_new_text_stats_and_image(self):
        n = self.sync([
            raw(10, "BT1-030", "Son Goku", "Draw 2.", power="15000"),  # texto y power
            raw(11, "BT10-002", "Vegeta", image="b"),  # imagen
            raw(12, "BT31-001", "Son Goku & Vegeta"),  # nueva
        ])
        self.assertEqual(n, 4)
        got = {(c.kind, c.card_number, c.field, c.before, c.after) for c in CardChange.objects.all()}
        self.assertIn(("text", "BT1-030", "texto", "Draw 1.", "Draw 2."), got)
        self.assertIn(("stats", "BT1-030", "power", "10000", "15000"), got)
        self.assertIn(("image", "BT10-002", "imagen", "https://e/a.png", "https://e/b.png"), got)
        self.assertIn(("new", "BT31-001", "", "", ""), got)

    def test_redownloading_the_same_cards_records_nothing(self):
        self.assertEqual(self.sync([raw(10, "BT1-030", "Son Goku", "Draw 1."), raw(11, "BT10-002", "Vegeta")]), 0)

    def test_first_import_does_not_flood_with_new_cards(self):
        self.assertEqual(self.sync([raw(12, "BT31-001", "Nueva")], catalog_was_empty=True), 0)


class ListChangesTests(TestCase):
    def setUp(self):
        upsert_cards([raw(10, "BT1-030", "Son Goku"), raw(11, "BT10-002", "Vegeta"), raw(12, "P-001", "Kame")])

    def test_banlist(self):
        self.assertEqual(changes.record_banlist_changes({}, [{"card_number": "BT1-030", "status": "banned"}]), 0)
        old = {"BT1-030": Legality.BANNED, "P-001": Legality.LIMITED}
        new = [{"card_number": "BT1-030", "status": Legality.LIMITED}, {"card_number": "BT10-002", "status": Legality.BANNED}]
        self.assertEqual(changes.record_banlist_changes(old, new), 3)
        got = {(c.card_number, c.kind, c.before, c.after, c.card_id) for c in CardChange.objects.all()}
        self.assertEqual(got, {
            ("BT1-030", "limited", "Banned", "Limited", 10),
            ("BT10-002", "banned", "Legal", "Banned", 11),
            ("P-001", "legal", "Limited", "Legal", 12),
        })

    def test_errata(self):
        old = {"BT1-030": "Fixed text."}
        new = [{"card_number": "BT1-030", "before": "Old", "after": "Fixed text."},
               {"card_number": "BT10-002", "before": "A", "after": "B"}]
        self.assertEqual(changes.record_errata_changes(old, new), 1)
        c = CardChange.objects.get()
        self.assertEqual((c.kind, c.card_number, c.before, c.after), ("errata", "BT10-002", "A", "B"))

    def test_rulings_compares_by_question_not_number(self):
        old = {("BT1-030", "Can you draw?")}
        new = [{"card_number": "BT1-030", "order": 1, "question": "New question?", "answer": "Yes."},
               {"card_number": "BT1-030", "order": 2, "question": "Can you draw?", "answer": "No."}]
        self.assertEqual(changes.record_ruling_changes(old, new), 1)
        c = CardChange.objects.get()
        self.assertEqual((c.kind, c.field, c.after), ("ruling", "P1", "New question?\n→ Yes."))


class ChangesApiTests(TestCase):
    def setUp(self):
        upsert_cards([raw(10, "BT1-030", "Son Goku")])
        old = timezone.now() - timedelta(days=5)
        CardChange.objects.create(kind="new", card_id=10, card_number="BT1-030", card_name="Son Goku", created_at=old)
        CardChange.objects.create(kind="banned", card_id=10, card_number="BT1-030", card_name="Son Goku",
                                  before="Legal", after="Banned")
        self.client = APIClient()

    def test_list_and_filter(self):
        data = self.client.get("/api/changes/").json()
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["results"][0]["kind"], "banned")  # lo más reciente primero
        self.assertEqual(data["results"][0]["kind_label"], "Banned")
        self.assertEqual({k["kind"]: k["count"] for k in data["kinds"]}["new"], 1)
        only_new = self.client.get("/api/changes/?kind=new").json()
        self.assertEqual([r["kind"] for r in only_new["results"]], ["new"])

    def test_count_since(self):
        since = (timezone.now() - timedelta(days=1)).isoformat()
        r = self.client.get("/api/changes/count/", {"since": since}).json()
        self.assertEqual(r["count"], 1)
        self.assertEqual(self.client.get("/api/changes/count/").json()["count"], 2)
