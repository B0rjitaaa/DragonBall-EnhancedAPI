from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from cards.banlist import apply_banlist, parse_banlist_html, store_entries
from cards.importer import upsert_cards
from cards.models import BanListEntry, Card

from .test_cards import GOKU, LOCMEM, PROMO, VEGETA

ENTRY = """
<div class="limitedCardList-inner cardColorBlue">
  <dl class="cardInfo notesCol">
    <dt class="title">Card No.</dt><dd class="contents">{no}</dd>
    <dt class="title">Card Name</dt><dd class="contents">{name}</dd>
  </dl>
  <div class="limitedCardCol">
    <div class="cellbox"><img src="../../images/cardlist/cardimg/{no}.png" alt="{no}"></div>
    <dl class="notesCol cellbox">
      <dt>Period</dt>
      <dd>North America, Oceania, Asia<br>{since}</dd>
      <dd>Europe (English version)<br>{since}</dd>
    </dl>
  </div>
</div>"""

PAGE = f"""
<h4 class="box-in subTitle">Banned/Limited Cards<br><small>(last updated on June 19, 2026)</small></h4>
<ul><li><a href="#bannedCardList">Banned Cards</a></li><li><a href="#limitedCardList">Limited</a></li></ul>
<section><div id="bannedCardList">
  <h5 class="points baseTxt section-in">Banned Card</h5>
  <p class="readTxt box-in">For official tournaments, this card cannot be put in your deck or side deck.</p>
  {ENTRY.format(no="BT1-030", name="Son Goku", since="From July 3 2026 onward.")}
  {ENTRY.format(no="BT5-118", name="A Child&#8217;s Wish", since="From June 1,2019 forward")}
</div></section>
<section><div id="bannedCardListBest-of-1Format">
  <h5>Banned Cards (Best-of-1 Format)</h5>
  <p class="readTxt">(No cards are currently banned for Best-of-1 Format.)</p>
</div></section>
<section><div id="limitedCardList">
  <h5 class="points baseTxt section-in">Limited Card</h5>
  <p class="readTxt box-in">You can only include a total 1 copy of this card between your deck and side deck at tournaments.</p>
  {ENTRY.format(no="BT10-002", name="Vegeta", since="From December 1, 2023 onward.")}
</div></section>
"""


class ParseTests(TestCase):
    def test_parse_official_page(self):
        updated, entries = parse_banlist_html(PAGE)
        self.assertEqual(updated, "June 19, 2026")
        self.assertEqual([(e["card_number"], e["status"], e["limit"]) for e in entries],
                         [("BT1-030", "banned", 0), ("BT5-118", "banned", 0), ("BT10-002", "limited", 1)])
        self.assertEqual(entries[1]["card_name"], "A Child’s Wish")
        self.assertEqual(entries[0]["since"], "From July 3 2026 onward.")


@override_settings(CACHES=LOCMEM)
class ApplyTests(TestCase):
    def setUp(self):
        cache.clear()
        BanListEntry.objects.all().delete()  # la migración carga la copia oficial
        upsert_cards([GOKU, VEGETA, PROMO])
        store_entries(parse_banlist_html(PAGE)[1], "June 19, 2026", "official")
        apply_banlist()

    def test_cards_marked(self):
        self.assertEqual(dict(Card.objects.values_list("id", "legality")),
                         {10: "banned", 11: "limited", 12: "legal"})

    def test_reimport_keeps_legality(self):
        upsert_cards([GOKU, VEGETA])
        self.assertEqual(Card.objects.get(id=10).legality, "banned")
        self.assertEqual(Card.objects.get(id=10).legality_since, "From July 3 2026 onward.")

    def test_unbanned_card_goes_back_to_legal(self):
        BanListEntry.objects.filter(card_number="BT1-030").delete()
        apply_banlist()
        self.assertEqual(Card.objects.get(id=10).legality, "legal")

    def test_api(self):
        client = APIClient()
        r = client.post("/api/cards/search/", {"query": {
            "field": "legality", "operator": "in", "value": ["banned", "limited"]}}, format="json")
        self.assertEqual({c["id"]: c["legality"] for c in r.json()["results"]}, {10: "banned", 11: "limited"})
        r = client.get("/api/banlist/").json()
        self.assertEqual(r["updated"], "June 19, 2026")
        self.assertEqual(len(r["entries"]), 3)
