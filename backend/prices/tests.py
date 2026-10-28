from decimal import Decimal
from unittest import mock

from django.test import TestCase

from cards.models import Card

from . import cardmarket, matching, pricing
from .models import CardmarketExpansion, CardmarketLink, CardmarketProduct
from .tasks import sync_prices

SET = "Unison Warrior Series -BOOST- Realm of the Gods [DBS-B16]"


def card(id, number, name, rarity="C", back="", colors=None, set_code="BT16", card_set=SET):
    return Card.objects.create(id=id, card_number=number, name=name, rarity_code=rarity, back_name=back,
                               colors=colors or ["Red"], set_code=set_code, card_set=card_set)


def product(id, name, exp=100, trend=1.0, avg30=None):
    return {"idProduct": id, "name": name, "idExpansion": exp, "idMetacard": 1, "dateAdded": "2022-02-25 16:53:58"}, \
        {"idProduct": id, "trend": trend, "avg30": avg30}


class ParseTests(TestCase):
    def test_parse_name(self):
        p = matching.parse_name("Android 21 // Self-Control Android 21")
        self.assertEqual((p.front, p.back, p.hint), ("android21", "selfcontrolandroid21", None))
        self.assertEqual(matching.parse_name("Vegeta (BT1-038)").hint, ("num", "BT1-038"))
        self.assertEqual(matching.parse_name("Dabura (BT06-048)").hint, ("num", "BT6-048"))
        self.assertEqual(matching.parse_name("Uub (BT11)").hint, ("set", "BT11"))
        self.assertEqual(matching.parse_name("Krillin (BT-7)").hint, ("set", "BT7"))
        self.assertEqual(matching.parse_name("Son Goku (Green)").hint, ("color", "Green"))

    def test_reference_price(self):
        price = cardmarket.reference_price
        # El menor de trend, la mediana de las medias y 3 veces el anuncio más barato.
        self.assertEqual(price({"trend": 11.6, "avg1": 10, "avg7": 14, "avg30": 16.5, "low": 11.89}), (Decimal("11.60"), False))
        # SS Son Goten P-428: una venta suelta de ~500 € infla trend y medias; se compra a 0,10 €.
        goten = {"trend": 51.23, "avg1": 0.59, "avg7": 77.51, "avg30": 25.09, "low": 0.10}
        self.assertEqual(price(goten), (Decimal("0.30"), False))
        # Senzu Bean común: trend disparado.
        self.assertEqual(price({"trend": 15.31, "avg1": 0.38, "avg7": 0.15, "avg30": 6.26, "low": 0.02}), (Decimal("0.06"), False))
        self.assertEqual(price({"trend": 0, "avg30": 16.5}), (Decimal("16.50"), False))  # sin trend ni anuncios
        self.assertEqual(price({"trend": 0, "low": 78}), (Decimal("78.00"), True))  # sin ventas: el anuncio, marcado
        self.assertEqual(price({}), (None, False))


class MatchingTests(TestCase):
    def setUp(self):
        self.mira = card(1, "BT16-148", "Super Mira, Diabolical Fusion", "SCR")
        self.goku_r = card(2, "BT16-003", "Son Goku", "R")
        self.goku_spr = card(3, "BT16-003", "Son Goku", "SPR")
        self.leader = card(4, "BT16-001", "Android 21", "UC", back="Self-Control Android 21")
        self.vegeta = card(5, "BT16-010", "Vegeta", colors=["Blue"])
        # Alt-art con el mismo número y rareza (V.1 y V.2): un producto cada una.
        self.a21_v1 = card(7, "BT16-149", "Android 21, Transcendental Predator", "SCR")
        self.a21_v2 = card(8, "BT16-149", "Android 21, Transcendental Predator", "SCR")
        self.other = card(6, "BT1-038", "Vegeta", set_code="BT1", card_set="Galactic Battle [DBS-B01]")
        rows = [
            product(10, "Super Mira, Diabolical Fusion", trend=11.6),
            product(11, "Son Goku", trend=0.2), product(12, "Son Goku", trend=30),  # normal y SPR
            product(13, "Android 21 // Self-Control Android 21"),
            product(14, "Vegeta (Blue)"),
            product(17, "Android 21, Transcendental Predator", trend=51.74),
            product(18, "Android 21, Transcendental Predator", trend=260),
            product(15, "Son Goku (FB01-001) [Fusion World]", exp=200),
            product(16, "Tien Shinhan (FB05-010) [Fusion World]"),  # colada por error en una expansión de Masters
        ]
        cardmarket.store([p for p, _ in rows], [g for _, g in rows])

    def links(self):
        return {link.card_id: (link.product_id, link.method) for link in CardmarketLink.objects.all()}

    def test_match(self):
        result = matching.match_all()
        self.assertEqual(CardmarketExpansion.objects.get(id=100).card_set, SET)
        self.assertTrue(CardmarketExpansion.objects.get(id=200).fusion_world)
        self.assertFalse(CardmarketExpansion.objects.get(id=100).fusion_world)  # una carta suelta no la marca
        self.assertEqual(self.links(), {
            1: (10, "auto"), 2: (11, "ordered"), 3: (12, "ordered"), 4: (13, "auto"), 5: (14, "auto"),
            7: (17, "ordered"), 8: (18, "ordered"),
        })
        self.assertEqual((result["auto"], result["ordered"]), (3, 4))
        self.assertEqual(CardmarketProduct.objects.get(id=10).price, Decimal("11.60"))

    def test_manual_links_and_expansions_are_kept(self):
        CardmarketLink.objects.create(card=self.goku_r, product_id=12, method="manual")
        CardmarketExpansion.objects.filter(id=100).update(manual=True, card_set=SET)
        matching.match_all()
        links = self.links()
        self.assertEqual(links[2], (12, "manual"))
        self.assertNotIn(3, links)  # el resto de su grupo ya no se deduce solo (sería emparejarla con la normal)

    def test_sync_task(self):
        payloads = [{"products": [product(20, "Super Mira, Diabolical Fusion")[0]]},
                    {"priceGuides": [product(20, "x", trend=9.5)[1]]}]
        with mock.patch("prices.cardmarket._get", side_effect=payloads), \
                mock.patch("prices.tasks.tcgplayer.fetch_rate", return_value=mock.Mock(usd_per_eur=Decimal("1.10"))), \
                mock.patch("prices.tasks.tcgplayer.sync", return_value=None), \
                mock.patch("prices.tasks.tcgplayer.match_all", return_value=0):
            result = sync_prices()
        self.assertEqual(result["products"], 1)
        self.assertEqual(CardmarketProduct.objects.get(id=20).price, Decimal("9.50"))


class ReviewTests(TestCase):
    """Página de revisión: tus cartas sin emparejar y los grupos «por orden» dudosos."""

    def setUp(self):
        from django.contrib.auth.models import User
        from django.test import Client

        from collection.models import CollectionEntry, Location

        here = Location.objects.create(name="Caja", kind="storage")
        self.promo = card(1, "P-003", "Son Goku", "PR", set_code="P", card_set="Promotion Cards")
        self.reprint = card(2, "P-003", "Son Goku", "PR", set_code="P", card_set="Promotion Cards")
        self.normal = card(3, "BT16-003", "Vegeta", "R")
        self.spr = card(4, "BT16-003", "Vegeta", "SPR")
        for c in (self.promo, self.normal, self.spr):
            CollectionEntry.objects.create(card=c, location=here, quantity=1)
        # 3 productos frente a 2 impresiones idénticas: no se deduce, a revisar.
        rows = [product(10, "Son Goku", exp=300, trend=5), product(11, "Son Goku", exp=300, trend=2),
                product(12, "Son Goku", exp=300, trend=1),
                product(20, "Vegeta", trend=30), product(21, "Vegeta", trend=0.5)]
        cardmarket.store([p for p, _ in rows], [g for _, g in rows])
        matching.match_all()
        self.client = Client()
        self.client.force_login(User.objects.create_superuser("admin", "a@a.es", "x"))

    def test_unmatched_and_candidates(self):
        from . import review

        total, pending = review.unmatched(10)
        self.assertEqual(total, 1)  # la promo (su reimpresión no la tienes)
        self.assertEqual({c.product.id for c in pending[0].candidates}, {10, 11, 12})

    def test_choose_applies_to_identical_reprints_and_is_kept(self):
        from . import review

        self.assertEqual(review.choose(self.promo, CardmarketProduct.objects.get(id=10)), 2)
        matching.match_all()
        self.assertEqual(CardmarketLink.objects.get(card=self.reprint).product_id, 10)
        self.assertEqual(review.unmatched(10)[0], 0)

    def test_not_in_cardmarket(self):
        r = self.client.post("/admin/prices/pricereview/choose/", {f"choice_{self.promo.id}": "none"})
        self.assertEqual(r.status_code, 302)
        link = CardmarketLink.objects.get(card=self.promo)
        self.assertEqual((link.product, link.method), (None, "none"))
        matching.match_all()  # sigue ahí
        self.assertTrue(CardmarketLink.objects.filter(card=self.promo, method="none").exists())

    def test_ordered_pairs_by_rarity_and_price_so_nothing_is_doubtful(self):
        from . import review

        links = {link.card_id: link.product_id for link in CardmarketLink.objects.filter(card_id__in=[3, 4])}
        self.assertEqual(links, {3: 21, 4: 20})  # la R con el barato, la SPR con el caro
        self.assertEqual(review.doubtful(), [])

    def test_fix_a_group_by_hand(self):
        self.client.post("/admin/prices/pricereview/group/", {"tab": "dudosos", "cards": [3, 4], "product_3": 20, "product_4": 21})
        self.assertEqual({link.card_id: (link.product_id, link.method) for link in CardmarketLink.objects.filter(card_id__in=[3, 4])},
                         {3: (20, "manual"), 4: (21, "manual")})

    def test_page(self):
        page = self.client.get("/admin/prices/pricereview/").content.decode()
        self.assertIn("P-003 · PR · Son Goku", page)
        self.assertIn("Emparejados por orden (0)", page)
        self.assertIn("Precios dudosos (0)", page)

    def test_manual_price(self):
        from prices.services import card_price, value_of
        from collection.models import CollectionEntry

        r = self.client.post("/admin/prices/pricereview/choose/", {f"choice_{self.promo.id}": "price", f"price_{self.promo.id}": "3,50"})
        self.assertEqual(r.status_code, 302)
        link = CardmarketLink.objects.get(card=self.reprint)  # también su reimpresión idéntica
        self.assertEqual((link.method, link.manual_price, link.product), ("price", Decimal("3.50"), None))
        matching.match_all()  # se queda
        promo = Card.objects.select_related("cardmarket__product").get(id=self.promo.id)
        self.assertEqual((card_price(promo)["eur"], card_price(promo)["manual"]), (3.5, True))
        value = value_of(CollectionEntry.objects.filter(card=self.promo))
        self.assertEqual((value["value"], value["copies_priced"]), (3.5, 1))
        self.client.post("/admin/prices/pricereview/choose/", {f"choice_{self.promo.id}": "price", f"price_{self.promo.id}": "abc"})
        self.assertEqual(CardmarketLink.objects.get(card=self.promo).manual_price, Decimal("3.50"))  # no cambia

    def test_saves_several_cards_at_once(self):
        other = card(5, "BT16-050", "Nappa", "C")
        from collection.models import CollectionEntry, Location

        CollectionEntry.objects.create(card=other, location=Location.objects.get(name="Caja"), quantity=1)
        r = self.client.post("/admin/prices/pricereview/choose/", {
            f"choice_{self.promo.id}": "10", f"choice_{other.id}": "price", f"price_{other.id}": "1.25", "page": "1",
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(CardmarketLink.objects.get(card=self.promo).product_id, 10)
        self.assertEqual(CardmarketLink.objects.get(card=other).manual_price, Decimal("1.25"))


    def test_mark_my_copies_as_fake(self):
        from collection.models import CollectionEntry
        from . import review

        CollectionEntry.objects.filter(card=self.promo).update(notes="pág. 3")
        r = self.client.post("/admin/prices/pricereview/choose/", {f"choice_{self.promo.id}": "fake"})
        self.assertEqual(r.status_code, 302)
        rows = list(CollectionEntry.objects.filter(card=self.promo).values_list("fake", "quantity", "notes"))
        self.assertEqual(rows, [(True, 1, "pág. 3")])
        self.assertEqual(review.unmatched(10)[0], 0)  # ya no hace falta su precio


class PairingAndSuspectTests(TestCase):
    def test_rarer_print_gets_the_dearer_product(self):
        # Ids al revés de lo habitual: la SPR se dio de alta antes que la normal en Cardmarket.
        normal = card(1, "BT24-001", "Vegeta", "UC")
        spr = card(2, "BT24-001", "Vegeta", "SPR")
        rows = [product(20, "Vegeta", trend=30), product(21, "Vegeta", trend=0.10)]
        cardmarket.store([p for p, _ in rows], [g for _, g in rows])
        matching.match_all()
        links = {link.card_id: link.product_id for link in CardmarketLink.objects.all()}
        self.assertEqual(links, {normal.id: 21, spr.id: 20})

    def test_listing_only_price_far_above_its_rarity_is_suspect(self):
        from collection.models import CollectionEntry, Location
        from prices.services import value_of

        here = Location.objects.create(name="Caja", kind="storage")
        cards, rows = [], []
        for i in range(25):  # comunes con ventas, a 0,05 €
            cards.append(card(100 + i, f"BT16-{i:03d}", f"Carta {i}", "C"))
            rows.append(product(200 + i, f"Carta {i}", trend=0.05))
        odd = card(300, "BT16-099", "Carta rara", "C")
        rows.append(({"idProduct": 400, "name": "Carta rara", "idExpansion": 100, "idMetacard": 1, "dateAdded": None},
                     {"idProduct": 400, "low": 9999}))  # solo un anuncio de relleno
        cardmarket.store([p for p, _ in rows], [g for _, g in rows])
        matching.match_all()
        pricing.refresh()
        self.assertTrue(CardmarketLink.objects.get(card=odd).suspect)
        self.assertFalse(CardmarketLink.objects.get(card=cards[0]).suspect)
        CollectionEntry.objects.create(card=odd, location=here, quantity=1)
        CollectionEntry.objects.create(card=cards[0], location=here, quantity=1)
        value = value_of(CollectionEntry.objects.all())
        self.assertEqual((value["value"], value["copies_unpriced"]), (0.05, 1))  # el dudoso no cuenta


class ListingOnlyTests(TestCase):
    """Cartas sin ventas (solo un anuncio): no suman en el valor, salvo confirmadas; y cambio de edición."""

    def setUp(self):
        from django.contrib.auth.models import User
        from django.test import Client

        from collection.models import CollectionEntry, Location

        self.box = Location.objects.create(name="Archivador", kind="binder")
        self.scr = card(1, "BT21-147", "Shenron, the Eternal Dragon", "SCR")
        self.gdr = card(2, "BT21-147", "Shenron, the Eternal Dragon", "GDR")
        rows = [product(10, "Shenron, the Eternal Dragon", trend=30),
                ({"idProduct": 11, "name": "Shenron, the Eternal Dragon", "idExpansion": 100, "idMetacard": 1,
                  "dateAdded": None}, {"idProduct": 11, "low": 2499})]
        cardmarket.store([p for p, _ in rows], [g for _, g in rows])
        matching.match_all()
        pricing.refresh()
        CollectionEntry.objects.create(card=self.gdr, location=self.box, quantity=1, notes="pág. 4")
        self.client = Client()
        self.client.force_login(User.objects.create_superuser("admin", "a@a.es", "x"))

    def value(self):
        from collection.models import CollectionEntry
        from prices.services import value_of

        return value_of(CollectionEntry.objects.all())

    def test_listing_only_is_apart(self):
        v = self.value()
        self.assertEqual((v["value"], v["value_listing"], v["copies_listing"]), (0, 2499.0, 1))
        self.assertIn("Cartas caras sin ventas (1)", self.client.get("/admin/prices/pricereview/").content.decode())

    def test_confirmed_listing_counts(self):
        self.client.post("/admin/prices/pricereview/choose/", {f"choice_{self.gdr.id}": "11", "tab": "sinventas"})
        self.assertEqual(self.value()["value"], 2499.0)

    def test_i_have_another_edition(self):
        from collection.models import CollectionEntry

        r = self.client.post("/admin/prices/pricereview/choose/", {f"choice_{self.gdr.id}": f"print:{self.scr.id}"})
        self.assertEqual(r.status_code, 302)
        rows = list(CollectionEntry.objects.values_list("card_id", "location_id", "quantity", "notes"))
        self.assertEqual(rows, [(self.scr.id, self.box.id, 1, "pág. 4")])
        v = self.value()
        self.assertEqual((v["value"], v["value_listing"]), (30.0, 0))


class CombineTests(TestCase):
    """Precio final de una carta con Cardmarket, TCGplayer y lo puesto a mano (pricing.combine)."""

    def link(self, price=None, is_low=False, method="auto", suspect=False, manual_price=None):
        product = CardmarketProduct(id=1, name="x", price=Decimal(price) if price else None, price_is_low=is_low)
        return CardmarketLink(product=product, method=method, suspect=suspect,
                              manual_price=Decimal(manual_price) if manual_price else None)

    def test_rules(self):
        c = lambda *a, **k: pricing.combine(*a, **k)
        D = Decimal
        self.assertEqual(c(self.link(manual_price="3"), D("100")), (D("3"), "manual", True))
        self.assertEqual(c(self.link("10"), D("8")), (D("10"), "cardmarket", True))  # Cardmarket manda
        self.assertEqual(c(self.link("10"), D("2.25")), (D("2.25"), "tcgplayer", True))  # TCGplayer < la mitad
        self.assertEqual(c(self.link("6", is_low=True), D("78")), (D("6"), "cardmarket", True))  # se compra por 6 €
        self.assertEqual(c(self.link("9999", is_low=True, suspect=True), D("20")), (D("20"), "tcgplayer", True))
        self.assertEqual(c(self.link("2499", is_low=True), None), (D("2499"), "cardmarket", False))  # solo anuncio
        self.assertEqual(c(None, D("4")), (D("4"), "tcgplayer", True))  # solo en TCGplayer
        self.assertIsNone(c(None, None))

    def test_history_only_on_change(self):
        from datetime import date
        from prices.models import CardPrice, PricePoint

        c1 = card(1, "BT1-001", "Son Goku")
        CardmarketLink.objects.create(card=c1, product=CardmarketProduct.objects.create(
            id=1, name="Son Goku", expansion=CardmarketExpansion.objects.create(id=1), price=Decimal("2")),
            method="auto")
        pricing.refresh(today=date(2026, 10, 1))
        pricing.refresh(today=date(2026, 10, 2))  # mismo precio: no se apunta
        CardmarketProduct.objects.filter(id=1).update(price=Decimal("3"))
        pricing.refresh(today=date(2026, 10, 9))
        self.assertEqual(list(PricePoint.objects.values_list("date", "eur")),
                         [(date(2026, 10, 1), Decimal("2")), (date(2026, 10, 9), Decimal("3"))])
        self.assertEqual(CardPrice.objects.get(card=c1).eur, Decimal("3"))
        self.assertAlmostEqual(pricing.change(c1.id, 7, today=date(2026, 10, 9)), 0.5)


class TcgMatchTests(TestCase):
    def test_origin_set_and_alternate_art(self):
        from prices import tcgplayer
        from prices.models import TcgLink, TcgProduct

        v1 = card(1, "BT20-149", "Android 21", "SCR")
        v2 = card(2, "BT20-149", "Android 21", "SCR")
        Card.objects.filter(id__in=[1, 2]).update(rarity="Secret Rare")
        common = card(3, "BT1-053", "Senzu Bean", "C")
        Card.objects.filter(id=3).update(rarity="Common")
        rows = [  # (id, grupo, nombre, número, rareza, variante)
            (10, 1, "Power Absorbed", "Android 21", "BT20-149", "Secret Rare", ""),
            (11, 1, "Power Absorbed", "Android 21 (Alternate Art)", "BT20-149", "Secret Rare", "Alternate Art"),
            (20, 2, "Galactic Battle", "Senzu Bean (2017)", "BT1-053", "Common", "2017"),
            (21, 3, "Mythic Booster", "Senzu Bean", "BT1-053", "Common", ""),  # reimpresión en otra caja
            (22, 2, "Galactic Battle", "Whis", "BT1-054", "Common", ""),
            (23, 3, "Mythic Booster", "Vegeta", "BT5-001", "Common", ""),
        ]
        for pid, gid, gname, name, number, rarity, variant in rows:
            TcgProduct.objects.create(id=pid, group_id=gid, group_name=gname, name=name, number=number,
                                      rarity=rarity, variant=variant, market_usd=Decimal("1"))
        tcgplayer.match_all()
        links = dict(TcgLink.objects.values_list("card_id", "product_id"))
        self.assertEqual(links, {v1.id: 10, v2.id: 11, common.id: 20})


class RadarTests(TestCase):
    def test_risers_fallers_and_expensive(self):
        from datetime import date, timedelta
        from rest_framework.test import APIClient
        from collection.models import CollectionEntry, Location
        from prices.models import CardPrice, PricePoint

        here = Location.objects.create(name="Caja", kind="storage")
        today = date.today()
        for i, (old, new) in enumerate([(10, 20), (10, 5), (0.02, 0.04), (50, 50)], start=1):
            c = card(i, f"BT1-00{i}", f"Carta {i}")
            CollectionEntry.objects.create(card=c, location=here, quantity=1)
            CardPrice.objects.create(card=c, eur=Decimal(str(new)), source="cardmarket", counts=True)
            PricePoint.objects.create(card=c, date=today - timedelta(days=20), eur=Decimal(str(old)))
            PricePoint.objects.create(card=c, date=today, eur=Decimal(str(new)))
        # Hace 7 días aún tenían el precio antiguo (cambió hoy): la subida entra en la ventana de 7 días.
        data = APIClient().get("/api/prices/radar/?days=7").json()
        self.assertEqual([(r["id"], round(r["change"], 2)) for r in data["risers"]], [(1, 1.0)])  # la de 0,04 € no
        self.assertEqual([(r["id"], round(r["change"], 2)) for r in data["fallers"]], [(2, -0.5)])
        self.assertEqual([r["id"] for r in data["expensive"]][:2], [4, 1])
        self.assertEqual(APIClient().get("/api/prices/radar/?days=7&scope=all").json()["scope"], "all")


class RadarFallbackTests(TestCase):
    def test_without_own_history_compares_with_cardmarket_averages(self):
        from rest_framework.test import APIClient
        from prices.models import CardPrice

        c = card(1, "BT1-001", "Son Goku")
        product = CardmarketProduct.objects.create(id=1, name="Son Goku", expansion=CardmarketExpansion.objects.create(id=1),
                                                   price=Decimal("14"), trend=Decimal("14"), avg7=Decimal("10"), avg30=Decimal("7"))
        CardmarketLink.objects.create(card=c, product=product, method="auto")
        CardPrice.objects.create(card=c, eur=Decimal("14"), source="cardmarket", counts=True)
        data = APIClient().get("/api/prices/radar/?days=30&scope=all").json()
        self.assertEqual(data["basis"], "cardmarket")
        self.assertEqual([(r["id"], r["before"], round(r["change"], 2)) for r in data["risers"]], [(1, 7.0, 1.0)])
        self.assertEqual(APIClient().get("/api/prices/radar/?days=7&scope=all").json()["risers"][0]["before"], 10.0)
