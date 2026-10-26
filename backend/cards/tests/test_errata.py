from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from cards import errata, rulings
from cards.importer import upsert_cards
from cards.models import Card, CardErrata, CardRuling

LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

ERRATA_HTML = """
<dt class="title">2025.02.28 [HISTORY OF Z] BT27-124 Justice Impact</dt>
<dd>
  <p class="readTxt txt-in">Card No:BT27-124</p>
  <p class="readTxt">Card Name:Justice Impact</p>
  <p class="txt-in"><img src="../../images/rule/errata-cards/BT27-124.png" alt="BT27-124"></p>
  <dl class="cardErrata"><dt>Card Errata</dt><dd>
    <div class="beforeCol"><b>Before</b><p class="txt-in">Old text here.</p></div>
    <div class="afterCol"><b>After</b><p class="txt-in">New fixed text.</p></div>
  </dd></dl>
  <dl class="errataNotes"><dt>Errata Notes</dt><dd><p>Some note.</p></dd></dl>
</dd>
<dt class="title">2024.01.01 [SET] BT1-030 Son Goku</dt>
<dd>
  <p class="readTxt">Card No:BT1-030</p>
  <p class="readTxt">Card Name:Son Goku</p>
  <dl class="cardErrata"><dt>Card Errata</dt><dd>
    <div class="beforeCol"><b>Before</b><p>A.</p></div>
    <div class="afterCol"><b>After</b><p>B.</p></div>
  </dd></dl>
</dd>
"""

FAQ_HTML = """
<h4 id="DBS-SD01" class="section-in subTitle"><small>STARTER DECK [DBS-SD01]</small></h4>
<h5 class="points baseTxt box-in">BT1-030 Son Goku</h5>
<dl class="faqCol">
  <dt><i>Q1.</i><span class="textCol">Can you draw?</span></dt>
  <dd><i>A1.</i><span class="textCol">No, you cannot.</span></dd>
</dl>
<dl class="faqCol">
  <dt><i>Q2.</i><span class="textCol">Second question?<i class="qaNewQIcon">NEW</i></span></dt>
  <dd><i>A2.</i><span class="textCol">Second answer.</span></dd>
</dl>
<h5 class="points baseTxt box-in">BT10-002 Vegeta</h5>
<dl class="faqCol">
  <dt><i>Q1.</i><span class="textCol">Vegeta question?</span></dt>
  <dd><i>A1.</i><span class="textCol">Vegeta answer.</span></dd>
</dl>
"""


class ParseTests(TestCase):
    def test_parse_errata(self):
        updated, entries = errata.parse_errata_html("updated on August 22, 2025)" + ERRATA_HTML)
        self.assertEqual(updated, "August 22, 2025")
        self.assertEqual(len(entries), 2)
        first = entries[0]
        self.assertEqual(first["card_number"], "BT27-124")
        self.assertEqual(first["card_name"], "Justice Impact")
        self.assertEqual(first["before"], "Old text here.")
        self.assertEqual(first["after"], "New fixed text.")
        self.assertEqual(first["notes"], "Some note.")
        self.assertEqual(first["date"], "2025.02.28")
        self.assertTrue(first["image_url"].endswith("errata-cards/BT27-124.png"))

    def test_parse_faq(self):
        _, entries = rulings.parse_faq_html(FAQ_HTML)
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0]["card_number"], "BT1-030")
        self.assertEqual(entries[0]["order"], 1)
        self.assertEqual(entries[0]["question"], "Can you draw?")
        self.assertEqual(entries[0]["answer"], "No, you cannot.")
        self.assertTrue(entries[1]["is_new"])
        self.assertEqual(entries[1]["order"], 2)
        self.assertEqual(entries[2]["card_number"], "BT10-002")
        self.assertEqual(entries[0]["set_label"], "STARTER DECK [DBS-SD01]")


def make(id, number, name):
    return {"id": id, "card_number": number, "card_name": name, "card_text": "",
            "image_url": f"https://e/{id}.png", "card_set": "Set",
            "card_config": [{"config_name": "Type", "value": "BATTLE"}]}


@override_settings(CACHES=LOCMEM)
class ApplyAndApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # La migración de datos carga el snapshot real; lo limpiamos para aislar el test.
        CardErrata.objects.all().delete()
        CardRuling.objects.all().delete()
        upsert_cards([make(10, "BT1-030", "Son Goku"), make(11, "BT10-002", "Vegeta"),
                      make(12, "P-001", "Kamehameha")])
        CardErrata.objects.create(card_number="BT1-030", card_name="Son Goku",
                                  before="A", after="B", source="test")
        CardRuling.objects.bulk_create([
            CardRuling(card_number="BT1-030", order=1, question="Q1?", answer="A1."),
            CardRuling(card_number="BT1-030", order=2, question="Q2?", answer="A2.", is_new=True),
        ])

    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_apply_marks_cards(self):
        self.assertEqual(errata.apply_errata(), 1)
        self.assertEqual(rulings.apply_rulings(), 1)
        self.assertTrue(Card.objects.get(id=10).has_errata)
        self.assertEqual(Card.objects.get(id=10).rulings_count, 2)
        self.assertFalse(Card.objects.get(id=11).has_errata)

    def test_detail_includes_errata_and_rulings(self):
        errata.apply_errata()
        rulings.apply_rulings()
        r = self.client.get("/api/cards/10/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["errata"]["after"], "B")
        self.assertEqual(len(data["rulings"]), 2)
        self.assertTrue(data["rulings"][1]["is_new"])

    def test_flag_filters(self):
        errata.apply_errata()
        rulings.apply_rulings()
        has_e = self.client.post("/api/cards/search/", {"query": {
            "field": "has_errata", "operator": "eq", "value": True}}, format="json")
        self.assertEqual([c["id"] for c in has_e.json()["results"]], [10])
        no_e = self.client.post("/api/cards/search/", {"query": {
            "field": "has_errata", "operator": "eq", "value": False}}, format="json")
        self.assertEqual(sorted(c["id"] for c in no_e.json()["results"]), [11, 12])
        has_qa = self.client.post("/api/cards/search/", {"query": {
            "field": "has_ruling", "operator": "eq", "value": True}}, format="json")
        self.assertEqual([c["id"] for c in has_qa.json()["results"]], [10])
