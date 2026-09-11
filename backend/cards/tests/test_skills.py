from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from cards.importer import upsert_cards
from cards.models import Card
from cards.skills import Catalog, parse_keyword_page

from .test_cards import GOKU, LEADER, LOCMEM, PROMO, VEGETA

PAGE = """
<h4 class="box-in subTitle">Keyword Skills<br><small>(last updated on Jul. 22, 2022)</small></h4>
<section id="Activate-Timing">
  <div class="clickSwitchingCol box-in">
    <div class="clickBtn tglBtn"><a>[Auto]</a></div>
    <div class="clickSwitchingCol_inner tglCol">
       <p class="box-in readTxt">
         This skill activates when its trigger conditions are met.</p>
    </div>
  </div>
</section>
<section id="Keyword-Skills">
  <div class="clickSwitchingCol box-in">
    <div class="clickBtn tglBtn"><a>[Over Realm X]</a></div>
    <div class="clickSwitchingCol_inner tglCol"><p class="readTxt">If you have at least X cards &amp; more.</p></div>
  </div>
</section>
<section id="Keywords">
  <div class="clickSwitchingCol box-in">
    <div class="clickBtn tglBtn"><a>[Once per Turn]</a></div>
    <div class="clickSwitchingCol_inner tglCol"><p>This skill on this card can only be activated once per turn.</p></div>
  </div>
</section>
<section id="ot-pc-lst"></section>
"""


class CatalogTests(TestCase):
    def setUp(self):
        self.catalog = Catalog.from_snapshot()

    def test_classify(self):
        cases = {
            "Over Realm 3": "Over Realm X", "Dark Over Realm 5": "Dark Over Realm X",
            "Once Per Turn": "Once per Turn", "Activate: Main": "Activate : Main",
            "Limit 1": "Limit X", "Empower Red 3/Yellow 3": "Empower ColorX",
            "Arrival Red/Green": "Arrival X/Y", "Warrior Of Universe 7": "Warrior of Universe 7",
            "Counter: Battle Card Attack": "Counter : Battle Card Attack", "Spirit Boost X": "Spirit Boost X",
        }
        for kw, official in cases.items():
            self.assertEqual(self.catalog.classify(kw)["name"], official, kw)
        self.assertIsNone(self.catalog.classify("Z-Stack 1"))

    def test_assign(self):
        out = self.catalog.assign(["Auto", "Once Per Turn", "Barrier", "Over Realm 4", "Z-Stack 2"])
        self.assertEqual(out, {"timing": ["Auto"], "keyword_skills": ["Barrier", "Over Realm X", "Z-Stack"],
                               "keyword_rules": ["Once per Turn"]})

    def test_parse_official_page(self):
        updated, entries = parse_keyword_page(PAGE)
        self.assertEqual(updated, "Jul. 22, 2022")
        self.assertEqual([(e["name"], e["category"]) for e in entries],
                         [("Auto", "timing"), ("Over Realm X", "skill"), ("Once per Turn", "keyword")])
        self.assertEqual(entries[1]["description"], "If you have at least X cards & more.")


@override_settings(CACHES=LOCMEM)
class SkillApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        upsert_cards([LEADER, GOKU, VEGETA, PROMO])

    def setUp(self):
        cache.clear()

    def test_cards_get_official_names(self):
        goku = Card.objects.get(id=10)
        self.assertEqual(goku.timing, ["Activate : Main/Battle", "Activate : Main", "Activate : Battle"])
        self.assertEqual(goku.keyword_skills, ["Barrier", "Blocker"])
        vegeta = Card.objects.get(id=11)
        self.assertEqual(vegeta.keyword_rules, ["Limit X"])

    def test_filter_and_endpoint(self):
        client = APIClient()
        r = client.post("/api/cards/search/", {"query": {
            "field": "keyword_rule", "operator": "has", "value": "Once per Turn"}}, format="json")
        self.assertEqual([c["id"] for c in r.json()["results"]], [1])
        data = client.get("/api/keyword-skills/").json()
        self.assertEqual(len(data["skills"]), 61)
        self.assertEqual(data["aliases"]["Once Per Turn"], "Once per Turn")
        self.assertIn("Ultimate", data["deck_rules"])
