from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from cards.importer import upsert_cards
from cards.models import Card
from cards.parsing import extract_keywords, normalize_keyword, parse_card
from cards.query import QueryError, tree_to_q

LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


def cfg(**values):
    names = {"Special_Trait": "Special Trait", "Color_Cost": "Color Cost", "Combo_power": "Combo power",
             "Combo_Energy": "Combo Energy", "Keyword_Skill": "Keyword Skill"}
    return [{"config_name": names.get(k, k), "value": v} for k, v in values.items()]


def make_card(id, number, name, text="", **config):
    return {"id": id, "card_number": number, "card_name": name, "card_text": text,
            "image_url": f"https://example.com/{id}.png", "card_set": "Test Set",
            "card_config": cfg(**config), "regulations": [{"id": 1, "title": "Constructed"}]}


LEADER = {
    **make_card(1, "BT20-023", "Android 18", "[Auto] When this card attacks, draw 1 card.",
                Type="LEADER", Color="Blue", Character="Android 18", Rarity="Uncommon[UC]",
                Power="10000", Special_Trait="Android", Era="Special"),
    "backcard_id": 2, "backcard_card_name": "Android 18, Impenetrable Rushdown",
    "backcard_card_text": "[Activate : Battle][Once per turn] This card gets +5000 power.",
    "backcard_card_config": cfg(Power="15000"),
}
GOKU = make_card(10, "BT1-030", "Son Goku", "[Barrier][Blocker] [Activate : Main/Battle] Draw 1.",
                 Type="BATTLE", Color="Red", Character="Son Goku", Rarity="Rare[R]", Energy="3",
                 Color_Cost="(Red)(Red)", Power="15000", Combo_power="10000", Combo_Energy="1",
                 Special_Trait="Saiyan/Earthling", Era="Saiyan Saga")
VEGETA = make_card(11, "BT10-002", "Vegeta", "[Counter : Play][Limit 1] [Barrier]",
                   Type="BATTLE", Color="Blue/Green", Character="Vegeta", Rarity="Super Rare[SR]",
                   Energy="1", Color_Cost="(Blue)", Power="5000", Special_Trait="Saiyan", Era="Saiyan Saga")
PROMO = make_card(12, "P-001", "Kamehameha", "[Counter : Attack] Negate the attack.",
                  Type="EXTRA", Color="Red", Rarity="Promotion[PR]", Energy="2", Color_Cost="(Red)")


class ParsingTests(TestCase):
    def test_keyword_normalization(self):
        self.assertEqual(normalize_keyword("Activate : Main"), "Activate: Main")
        self.assertEqual(normalize_keyword("Once per turn"), "Once Per Turn")
        self.assertEqual(normalize_keyword("Activate ： Battle"), "Activate: Battle")
        self.assertEqual(normalize_keyword("Empower (Red)3"), "Empower Red 3")
        self.assertEqual(normalize_keyword("Activate Main"), "Activate: Main")
        self.assertEqual(normalize_keyword("Union Potara"), "Union-Potara")

    def test_attribute_variants(self):
        from cards.parsing import normalize_attr
        self.assertEqual(normalize_attr("Dr.Myuu"), "Dr. Myuu")
        self.assertEqual(normalize_attr("Universe7"), "Universe 7")
        self.assertEqual(normalize_attr("DBS：SUPER HERO Saga"), "DBS : SUPER HERO Saga")
        self.assertEqual(normalize_attr("Son Gohan : Adolescence"), "Son Gohan : Adolescence")

    def test_keywords_and_families(self):
        kws, fams = extract_keywords("[Activate : Main/Battle][Limit 1][+1][Counter : Play][Revive Blue/Green]")
        self.assertIn("Activate: Main/Battle", kws)
        self.assertIn("Activate: Main", kws)
        self.assertIn("Activate: Battle", kws)
        self.assertIn("Limit 1", kws)
        self.assertNotIn("+1", kws)
        self.assertEqual(set(fams), {"Activate", "Limit", "Counter", "Revive"})

    def test_parse_card(self):
        c = parse_card(GOKU)
        self.assertEqual((c["series"], c["set_number"], c["collector_number"], c["set_code"]), ("BT", 1, 30, "BT1"))
        self.assertEqual((c["rarity"], c["rarity_code"]), ("Rare", "R"))
        self.assertEqual(c["special_traits"], ["Saiyan", "Earthling"])
        self.assertEqual(c["color_cost_colors"], ["Red", "Red"])
        self.assertEqual((c["energy"], c["power"], c["combo_power"], c["combo_energy"]), (3, 15000, 10000, 1))

    def test_parse_leader_back(self):
        c = parse_card(LEADER)
        self.assertEqual(c["back_power"], 15000)
        self.assertIn("Once Per Turn", c["keywords"])
        self.assertIsNone(c["energy"])


@override_settings(CACHES=LOCMEM)
class QueryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        upsert_cards([LEADER, GOKU, VEGETA, PROMO])

    def ids(self, tree):
        return set(Card.objects.filter(tree_to_q(tree)).values_list("id", flat=True))

    def test_array_has_all_is_and(self):
        tree = {"field": "keyword", "operator": "has_all", "value": ["Barrier", "Blocker"]}
        self.assertEqual(self.ids(tree), {10})

    def test_nested_or_and(self):
        tree = {"op": "or", "children": [
            {"op": "and", "children": [
                {"field": "type", "operator": "eq", "value": "LEADER"},
                {"field": "color", "operator": "has", "value": "Blue"}]},
            {"op": "and", "children": [
                {"field": "keyword_family", "operator": "has", "value": "Counter"},
                {"field": "energy", "operator": "lte", "value": 1}]},
        ]}
        self.assertEqual(self.ids(tree), {1, 11})

    def test_not_and_between(self):
        tree = {"op": "and", "children": [
            {"field": "energy", "operator": "between", "value": [1, 3]},
            {"field": "color", "operator": "has", "value": "Red", "not": True}]}
        self.assertEqual(self.ids(tree), {11})

    def test_text_searches_both_faces(self):
        self.assertEqual(self.ids({"field": "name", "operator": "contains", "value": "rushdown"}), {1})

    def test_invalid(self):
        for bad in [{"field": "nope", "operator": "eq", "value": 1},
                    {"field": "energy", "operator": "has", "value": 1},
                    {"field": "energy", "operator": "eq", "value": "abc"},
                    {"op": "xor", "children": []}]:
            with self.assertRaises(QueryError):
                tree_to_q(bad)

    def test_depth_limit(self):
        tree = {"field": "energy", "operator": "eq", "value": 1}
        for _ in range(7):
            tree = {"op": "and", "children": [tree]}
        with self.assertRaises(QueryError):
            tree_to_q(tree)


@override_settings(CACHES=LOCMEM)
class ApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        upsert_cards([LEADER, GOKU, VEGETA, PROMO])

    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_list_with_params(self):
        r = self.client.get("/api/cards/", {"color": ["Red", "Green"], "energy_max": 2})
        self.assertEqual(r.status_code, 200)
        self.assertEqual({c["id"] for c in r.json()["results"]}, {11, 12})

    def test_natural_ordering(self):
        r = self.client.get("/api/cards/")
        self.assertEqual([c["card_number"] for c in r.json()["results"]],
                         ["BT1-030", "BT10-002", "BT20-023", "P-001"])

    def test_search_post(self):
        r = self.client.post("/api/cards/search/", {
            "q": "goku", "query": {"field": "special_trait", "operator": "has", "value": "Saiyan"},
            "ordering": "-power"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["count"], 1)

    def test_free_text_ignores_brackets(self):
        # El texto real es "[Barrier][Blocker] [Activate : Main/Battle] Draw 1."
        for q in ["barrier blocker", "Activate: Main/Battle draw", "[Blocker]", "son goku", "BT1-030"]:
            r = self.client.post("/api/cards/search/", {"q": q}, format="json")
            self.assertEqual([c["id"] for c in r.json()["results"]], [10], q)

    def test_text_condition_ignores_brackets(self):
        r = self.client.post("/api/cards/search/", {"query": {
            "field": "text", "operator": "contains", "value": "counter: play limit 1"}}, format="json")
        self.assertEqual([c["id"] for c in r.json()["results"]], [11])

    def test_search_null_query(self):
        r = self.client.post("/api/cards/search/", {"q": "", "query": None}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["count"], 4)

    def test_search_invalid_query_returns_400(self):
        r = self.client.post("/api/cards/search/", {"query": {"field": "x"}}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_facets(self):
        r = self.client.post("/api/facets/", {"query": {"field": "color", "operator": "has", "value": "Red"}},
                             format="json")
        data = r.json()
        self.assertEqual(data["total"], 2)
        types = {v["value"]: v["count"] for v in data["facets"]["type"]["values"]}
        self.assertEqual(types, {"BATTLE": 1, "EXTRA": 1})

    def test_facets_only(self):
        r = self.client.post("/api/facets/", {"only": ["color"]}, format="json")
        self.assertEqual(set(r.json()["facets"]), {"color"})
        self.assertEqual(self.client.post("/api/facets/", {"only": ["nope"]}, format="json").status_code, 400)

    def test_detail_and_fields(self):
        self.assertEqual(self.client.get("/api/cards/1/").json()["back_power"], 15000)
        keys = {f["key"] for f in self.client.get("/api/fields/").json()}
        self.assertTrue({"keyword", "energy", "special_trait"} <= keys)

    def test_sync_requires_admin(self):
        self.assertEqual(self.client.post("/api/sync/").status_code, 403)
