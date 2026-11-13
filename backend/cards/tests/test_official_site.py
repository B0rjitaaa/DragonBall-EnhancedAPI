from unittest import mock

from django.test import TestCase

from cards import official_site
from cards.importer import upsert_cards
from cards.models import Card, CardChange
from cards.printings import CUSTOM_ID_START
from collection.models import CollectionEntry, Location, Want
from decks.models import DeckVersion, DeckVersionCard, Match

IMG = "../../images/cardlist/common"
LEADER = f"""
<li>
  <dl class="cardListCol cardColorRed csrdTypeLEADER cardFront">
    <dt class="cardNumber">BT32-001</dt>
    <dd class="cardName">Inoshikacho &amp; Tien Shinhan</dd>
    <dd class="leftCol clearfix">
      <div class="cardimg"><img src="../../images/cardlist/cardimg/BT32-001.png" alt="x" class="zoomcard" /></div>
      <dl class="seriesCol"><dt>Series</dt><dd>ULTRA BOUT Series 05<br>CHROMATIC ASCENSION</dd></dl>
      <dl class="rarityCol"><dt>Rarity</dt><dd>Uncommon[UC]</dd></dl>
    </dd>
    <dd class="rightCol clearfix">
      <dl class="typeCol"><dt>Type</dt><dd>LEADER</dd></dl>
      <dl class="colorCol"><dt>Color</dt><dd>Red</dd></dl>
      <dl class="powerCol"><dt>Power</dt><dd>10000</dd></dl>
      <dl class="characterCol"><dt>Character</dt><dd>Tien Shinhan/Inoshikacho</dd></dl>
      <dl class="specialTraitCol"><dt>Special Trait</dt><dd>Earthling/Monster</dd></dl>
      <dl class="eraCol"><dt>Era</dt><dd>Young Son Goku Saga</dd></dl>
      <dl class="skillCol"><dt>Skill</dt>
        <dd><img src="{IMG}/Auto.png" alt="Auto" class="skillText" /> When a card KOs, draw.<br><img src="{IMG}/Activate-Main.png" alt="Activate Main" class="skillText" /><img src="{IMG}/Once-per-turn.png" alt="Once per turn" class="skillText" /><img src="{IMG}/Burst_3.png" alt="Burst 3" class="skillText" /> Choose a red ＜Inoshikacho＞ card.</dd>
      </dl>
    </dd>
  </dl>
  <div class="cardBack">
  <dl class="cardListCol cardColorRed csrdTypeLEADER">
    <dt class="cardNumber">BT32-001</dt>
    <dd class="cardName">Inoshikacho &amp; Son Goku, Rescue</dd>
    <dd class="leftCol clearfix">
      <div class="cardimg"><img src="../../images/cardlist/cardimg/BT32-001_b.png" alt="x" class="zoomcard" /></div>
    </dd>
    <dd class="rightCol clearfix">
      <dl class="typeCol"><dt>Type</dt><dd>LEADER</dd></dl>
      <dl class="powerCol"><dt>Power</dt><dd>15000</dd></dl>
      <dl class="skillCol"><dt>Skill</dt><dd><img src="{IMG}/Auto.png" alt="Auto" class="skillText" /> When one of your cards attacks, draw 1 card.</dd></dl>
    </dd>
  </dl>
  </div>
</li>
"""
BATTLE = f"""
<li>
  <dl class="cardListCol cardColorRed csrdTypeBATTLE cardFront">
    <dt class="cardNumber">BT32-002</dt>
    <dd class="cardName">Fasha, Enduring Will</dd>
    <dd class="leftCol clearfix">
      <div class="cardimg"><img src="../../images/cardlist/cardimg/BT32-002.png" alt="x" class="zoomcard" /></div>
      <dl class="seriesCol"><dt>Series</dt><dd>ULTRA BOUT Series 05<br>CHROMATIC ASCENSION</dd></dl>
      <dl class="rarityCol"><dt>Rarity</dt><dd>Common[C]</dd></dl>
    </dd>
    <dd class="rightCol clearfix">
      <dl class="typeCol"><dt>Type</dt><dd>BATTLE</dd></dl>
      <dl class="colorCol"><dt>Color</dt><dd>Red</dd></dl>
      <dl class="powerCol"><dt>Power</dt><dd>4000</dd></dl>
      <dl class="energyCol"><dt>Energy<span class="brk">(Color Cost)</span></dt><dd>2(<img src="{IMG}/red_ball.png" alt="" class="colorCostBall" /><img src="{IMG}/red_ball.png" alt="" class="colorCostBall" />)</dd></dl>
      <dl class="comboEnergyCol"><dt>Combo Energy</dt><dd>-</dd></dl>
      <dl class="comboPowerCol"><dt>Combo Power</dt><dd>5000</dd></dl>
      <dl class="characterCol"><dt>Character</dt><dd>Fasha</dd></dl>
      <dl class="specialTraitCol"><dt>Special Trait</dt><dd>Saiyan/Bardock's Crew</dd></dl>
      <dl class="eraCol"><dt>Era</dt><dd>Bardock Saga</dd></dl>
      <dl class="skillCol"><dt>Skill</dt>
        <dd><img src="{IMG}/Endure_2.png" alt="Endure 2" class="skillText" />(When this card is played, …)<br><img src="{IMG}/Activate-Battle.png" alt="Activate Battle" class="skillText" /><img src="{IMG}/Limit_1.png" alt="Limit 1" class="skillText" /><img src="{IMG}/one.png" alt="one" class="skillTextBall" /><img src="{IMG}/black_ball.png" alt="" class="skillTextBall" />, if your Leader is red: Play this card.<br><img src="{IMG}/Auto.png" alt="Auto" class="skillText" /><img src="{IMG}/Release_4.png" alt="Release 4" class="skillText" />(Remove the specified number of energy markers.) When this card attacks, draw 1 card.</dd>
      </dl>
    </dd>
  </dl>
</li>
"""


def page(*cards: str, padding: int = 0) -> str:
    # import_set pide un mínimo de cartas: se rellena con copias de otra numeración.
    extra = [BATTLE.replace("BT32-002", f"BT32-{100 + i:03d}") for i in range(padding)]
    return '<ul class="list-inner">' + "".join([*cards, *extra]) + "</ul>"


@mock.patch("scanner.tasks.build_fingerprints.delay", mock.Mock())
class ParseTests(TestCase):
    def test_cards_in_tcgplus_format(self):
        leader, battle = official_site.parse_cardlist(page(LEADER, BATTLE))
        self.assertEqual(leader["card_number"], "BT32-001")
        self.assertEqual(leader["card_name"], "Inoshikacho & Tien Shinhan")
        self.assertEqual(leader["card_set"], "ULTRA-BOUT Series 05-CHROMATIC ASCENSION-[DBS-B32]")
        self.assertEqual(leader["image_url"], "https://www.dbs-cardgame.com/images/cardlist/cardimg/BT32-001.png")
        self.assertEqual(leader["card_text"], "[Auto] When a card KOs, draw.<br>[Activate: Main][Once Per Turn][Burst 3] "
                                              "Choose a red &lt;Inoshikacho&gt; card.")
        self.assertEqual(leader["backcard_card_name"], "Inoshikacho & Son Goku, Rescue")
        self.assertTrue(leader["backcard_image_url"].endswith("BT32-001_b.png"))
        self.assertNotIn("backcard_card_name", battle)
        self.assertEqual(battle["card_text"],
                         "[Endure 2](When this card is played, …)<br>[Activate: Battle][Limit 1](1)(Black), if your "
                         "Leader is red: Play this card.<br>[Auto][Release 4](Remove the specified number of energy "
                         "markers.) When this card attacks, draw 1 card.")

    def test_import_creates_provisional_cards(self):
        result = official_site.import_set("428032", page=page(LEADER, BATTLE, padding=20))
        self.assertEqual(result["created"], 22)
        leader = Card.objects.get(card_number="BT32-001")
        battle = Card.objects.get(card_number="BT32-002")
        self.assertGreaterEqual(leader.id, CUSTOM_ID_START)
        self.assertEqual((leader.card_type, leader.power, leader.back_power), ("LEADER", 10000, 15000))
        self.assertTrue(leader.has_back)
        self.assertEqual((battle.energy, battle.color_cost, battle.combo_energy, battle.combo_power, battle.power),
                         (2, "(Red)(Red)", 0, 5000, 4000))
        self.assertEqual(battle.special_traits, ["Saiyan", "Bardock's Crew"])
        self.assertEqual(battle.keyword_skills, ["Endure X"])
        self.assertIn("Release X", battle.keyword_rules)
        self.assertEqual(CardChange.objects.filter(kind=CardChange.Kind.NEW).count(), 22)
        # Volver a importar actualiza las mismas cartas (no crea otras)
        again = official_site.import_set("428032", page=page(LEADER, BATTLE, padding=20))
        self.assertEqual((again["created"], Card.objects.count()), (0, 22))

    def test_variants_keep_the_card_number(self):
        variant = LEADER.replace("<dt class=\"cardNumber\">BT32-001</dt>", "<dt class=\"cardNumber\">BT32-001_PR</dt>", 1) \
            .replace("Uncommon[UC]", "Special Leader Rare[SLR]").replace("BT32-001.png", "BT32-001_PR.png")
        official_site.import_set("428032", page=page(LEADER, variant, BATTLE, padding=20))
        cards = Card.objects.filter(card_number="BT32-001").order_by("id")
        self.assertEqual([(c.rarity_code, c.raw["official_site"]["number"]) for c in cards],
                         [("UC", "BT32-001"), ("SLR", "BT32-001_PR")])
        self.assertTrue(all(c.has_back for c in cards))
        self.assertTrue(cards[1].image_url.endswith("BT32-001_PR.png"))
        # Con la normal ya en TCG+, solo se salta esa; la variante sigue
        Card.objects.filter(card_number="BT32-001", rarity_code="UC").delete()
        upsert_cards([{"id": 120010, "card_number": "BT32-001", "card_name": "TCG+",
                       "card_config": [{"config_name": "Rarity", "value": "Uncommon[UC]"}]}])
        again = official_site.import_set("428032", page=page(LEADER, variant, BATTLE, padding=20))
        self.assertEqual((again["in_tcgplus"], again["created"]), (1, 0))
        # Y la sustitución no mete la variante en la normal si TCG+ no tiene su rareza
        self.assertEqual(official_site.reconcile(), {"merged": 0})

    def test_too_few_cards_is_an_error(self):
        with self.assertRaises(RuntimeError):
            official_site.import_set("428032", page=page(LEADER))


@mock.patch("scanner.tasks.build_fingerprints.delay")
class ReconcileTests(TestCase):
    def setUp(self):
        with mock.patch("scanner.tasks.build_fingerprints.delay"):
            official_site.import_set("428032", page=page(LEADER, BATTLE, padding=20))
        self.provisional = Card.objects.get(card_number="BT32-002")
        self.leader = Card.objects.get(card_number="BT32-001")
        self.box = Location.objects.create(name="Caja", kind="storage")
        self.deck = Location.objects.create(name="Mazo", kind="deck")
        CollectionEntry.objects.create(card=self.provisional, location=self.box, quantity=2, notes="pág. 3")
        CollectionEntry.objects.create(card=self.provisional, location=self.deck, quantity=1)
        Want.objects.create(card=self.provisional, quantity=2)
        version = DeckVersion.objects.create(deck=self.deck, number=1)
        DeckVersionCard.objects.create(version=version, card=self.provisional, section="main", quantity=4)
        Match.objects.create(version=version, played_on="2026-11-13", result="win",
                             opponent_leader_bandai_id=self.leader.id)

    def tcgplus(self, card_id, number, rarity="Common[C]"):
        upsert_cards([{"id": card_id, "card_number": number, "card_name": "TCG+",
                       "card_config": [{"config_name": "Rarity", "value": rarity}],
                       "card_set": "ULTRA-BOUT Series 05-CHROMATIC ASCENSION-[DBS-B32]"}])
        return Card.objects.get(id=card_id)

    def test_nothing_to_do_while_tcgplus_doesnt_have_it(self, _):
        self.assertEqual(official_site.reconcile(), {"merged": 0})
        self.assertTrue(Card.objects.filter(id=self.provisional.id).exists())

    def test_moves_everything_to_the_tcgplus_card(self, _):
        alt = self.tcgplus(120001, "BT32-002", "Special Rare[SPR]")
        base = self.tcgplus(120002, "BT32-002")
        leader = self.tcgplus(120003, "BT32-001", "Uncommon[UC]")
        CollectionEntry.objects.create(card=base, location=self.box, quantity=1)  # ya tenía una de TCG+ ahí
        self.assertEqual(official_site.reconcile(), {"merged": 2})

        self.assertFalse(Card.objects.filter(id__in=[self.provisional.id, self.leader.id]).exists())
        # Va a la impresión de su misma rareza (la del sobre), no a la alternativa
        self.assertFalse(CollectionEntry.objects.filter(card=alt).exists())
        self.assertEqual(CollectionEntry.objects.get(card=base, location=self.box).quantity, 3)
        self.assertEqual(CollectionEntry.objects.get(card=base, location=self.box).notes, "pág. 3")
        self.assertEqual(CollectionEntry.objects.get(card=base, location=self.deck).quantity, 1)
        self.assertEqual(Want.objects.get(card=base).quantity, 2)
        self.assertEqual(DeckVersionCard.objects.get(card=base).quantity, 4)
        self.assertEqual(Match.objects.get().opponent_leader_bandai_id, leader.id)
        # La novedad sigue (con la carta de TCG+) y no se repite
        self.assertEqual(CardChange.objects.filter(kind=CardChange.Kind.NEW, card=base).count(), 1)
