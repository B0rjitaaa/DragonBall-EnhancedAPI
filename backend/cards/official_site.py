"""Colecciones de la web oficial (dbs-cardgame.com) que Bandai TCG+ aún no publica.

Cuando sale una colección, la web oficial la enseña días o semanas antes que la API de TCG+ (de donde
sale el catálogo). `import_set()` la trae desde el buscador de la web oficial y guarda cada carta con
el mismo formato que las de TCG+ (para que `parse_card` saque habilidades, costes, etc. igual), como
**carta provisional**: id >= CUSTOM_ID_START y `raw["official_site"]`.

Cuando TCG+ publica la carta, `reconcile()` (lo llama la sincronización) pasa a la carta de TCG+ todo lo
que apunta a la provisional (copias de la colección, wants, listas de mazos, side, partidas, escáner,
novedades e historial) y la borra. Así no quedan duplicadas.
"""
from __future__ import annotations

import html as htmllib
import logging
import re
from datetime import date

from django.db import transaction
from django.db.models import Case, IntegerField, Value, When

from .changes import record_card_changes, snapshot_cards
from .importer import invalidate_facets, upsert_cards
from .models import Card, CardChange
from .printings import CUSTOM_ID_START

logger = logging.getLogger(__name__)

SITE = "https://www.dbs-cardgame.com"
CARDLIST_URL = f"{SITE}/asia/cardlist/index.php?search=true"
# Las rutas de la web son relativas a /asia/cardlist/ («../../images/…»).
IMAGE_BASE = f"{SITE}/images/"
REGULATIONS = [{"id": 1, "title": "Constructed"}, {"id": 117, "title": "Deck Limited"}, {"id": 116, "title": "Draft"}]
MIN_EXPECTED = 20

# Iconos de la web oficial → cómo los escribe TCG+ en el texto de la carta.
ICON_NAMES = {
    "Activate Main": "Activate: Main",
    "Activate Battle": "Activate: Battle",
    "Once per turn": "Once Per Turn",
    "Counter Attack": "Counter: Attack",
    "Counter Play": "Counter: Play",
    "Counter Counter": "Counter: Counter",
}
# Bolas de coste genérico (one.png…) → (1)…
NUMBER_WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
                "eight": 8, "nine": 9, "ten": 10}

LI_RE = re.compile(r"<li>\s*(<dl class=\"cardListCol[^\"]*cardFront\".*?)</li>", re.S)
BACK_RE = re.compile(r'<div class="cardBack">(.*)', re.S)
IMG_RE = re.compile(r"<img\s[^>]*>", re.S)
ATTR_RE = re.compile(r'(\w+)="([^"]*)"')
TAG_RE = re.compile(r"<[^>]+>")
CARD_SET_RE = re.compile(r"^(\D+)(\d+)$")


def _field(block: str, css: str) -> str:
    """El contenido (HTML) del <dd> de un campo («typeCol», «powerCol»…), o ''."""
    m = re.search(rf'<dl class="{css}">\s*<dt>.*?</dt>\s*<dd>(.*?)</dd>', block, re.S)
    return m.group(1).strip() if m else ""


def _plain(fragment: str) -> str:
    return re.sub(r"\s+", " ", htmllib.unescape(TAG_RE.sub(" ", fragment.replace("<br>", " ")))).strip()


def _icon(tag: str) -> str:
    """Un <img> del texto: habilidad → «[Auto]», bola de color → «(Red)», bola de número → «(1)»."""
    attrs = dict(ATTR_RE.findall(tag))
    src, alt = attrs.get("src", ""), htmllib.unescape(attrs.get("alt", "")).strip()
    ball = re.search(r"/([a-z]+)_ball\.png", src)
    if ball:
        return f"({ball.group(1).capitalize()})"
    if alt.lower() in NUMBER_WORDS:
        return f"({NUMBER_WORDS[alt.lower()]})"
    if alt == "X" or src.endswith("/X.png"):
        return "(X)"
    if not alt:
        return ""
    if alt.upper().startswith("UNISON"):
        alt = alt[len("UNISON"):].strip()  # TCG+ escribe solo «[+1]» / «[-2]»
    return f"[{ICON_NAMES.get(alt, alt)}]"


def skill_text(fragment: str) -> str:
    """El texto de habilidades de la web oficial con el formato de TCG+ («[Auto] … <br>[Activate: Main]…»)."""
    text = IMG_RE.sub(lambda m: _icon(m.group(0)), fragment)
    lines = []
    for line in re.split(r"<br\s*/?>", text):
        line = htmllib.unescape(TAG_RE.sub("", line))
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)
    text = "<br>".join(lines)
    # TCG+ escribe los nombres de carta entre &lt; &gt;; la web oficial, con ＜ ＞ de ancho completo.
    return text.replace("<br>", "\0").replace("<", "&lt;").replace(">", "&gt;").replace("\0", "<br>") \
        .replace("＜", "&lt;").replace("＞", "&gt;")


def _energy(fragment: str) -> tuple[str | None, str]:
    """«1(<bola roja>)» → ('1', '(Red)')."""
    m = re.match(r"\s*(\d+|-)", TAG_RE.sub("", fragment))
    energy = m.group(1) if m and m.group(1) != "-" else None
    colors = "".join(f"({c.capitalize()})" for c in re.findall(r"/([a-z]+)_ball\.png", fragment))
    return energy, colors


def _image(block: str) -> str:
    m = re.search(r'<div class="cardimg">\s*<img src="([^"]+)"', block)
    if not m:
        return ""
    src = m.group(1)
    return src if src.startswith("http") else IMAGE_BASE + src.split("images/", 1)[-1]


def _config(block: str) -> list[dict]:
    energy, color_cost = _energy(_field(block, "energyCol"))
    card_type = _plain(_field(block, "typeCol"))
    combo_energy = _plain(_field(block, "comboEnergyCol"))
    if combo_energy == "-":
        # TCG+ pone 0 en las Battle; las demás no tienen combo.
        combo_energy = "0" if card_type.upper() == "BATTLE" else ""
    values = {
        "Type": card_type,
        "Color": _plain(_field(block, "colorCol")),
        "Character": _plain(_field(block, "characterCol")),
        "Rarity": _plain(_field(block, "rarityCol")),
        "Energy": energy,
        "Color Cost": color_cost,
        "Combo Energy": combo_energy,
        "Combo power": _plain(_field(block, "comboPowerCol")).replace("-", ""),
        "Power": _plain(_field(block, "powerCol")).replace("-", ""),
        "Special Trait": _plain(_field(block, "specialTraitCol")),
        "Era": _plain(_field(block, "eraCol")),
    }
    return [{"config_name": k, **({"value": v} if v else {})} for k, v in values.items()]


def card_set_name(series: str, card_number: str) -> str:
    """«ULTRA BOUT Series 05<br>CHROMATIC ASCENSION» + BT32-001 → «ULTRA-BOUT Series 05-CHROMATIC ASCENSION-[DBS-B32]»
    (como lo escribe TCG+, para que la colección sea la misma cuando llegue)."""
    parts = [_plain(p) for p in re.split(r"<br\s*/?>", series) if _plain(p)]
    name = "-".join(parts).replace("ULTRA BOUT", "ULTRA-BOUT")
    prefix = card_number.split("-", 1)[0]
    m = CARD_SET_RE.match(prefix)
    if m and m.group(1) == "BT":
        name += f"-[DBS-B{m.group(2)}]"
    return name


def parse_cardlist(page: str) -> list[dict]:
    """Las cartas de una página del buscador oficial, en el formato del detalle de TCG+ (sin «id»)."""
    cards = []
    for block in LI_RE.findall(page):
        back_match = BACK_RE.search(block)
        front = block[:back_match.start()] if back_match else block
        back = back_match.group(1) if back_match else ""
        number = _plain(re.search(r'<dt class="cardNumber">(.*?)</dt>', front, re.S).group(1))
        data = {
            "card_number": number,
            "card_name": _plain(re.search(r'<dd class="cardName">(.*?)</dd>', front, re.S).group(1)),
            "card_text": skill_text(_field(front, "skillCol")),
            "image_url": _image(front),
            "card_set": card_set_name(_field(front, "seriesCol"), number),
            "card_config": _config(front),
            "regulations": REGULATIONS,
        }
        if back:
            data.update({
                "backcard_card_number": number,
                "backcard_card_name": _plain(re.search(r'<dd class="cardName">(.*?)</dd>', back, re.S).group(1)),
                "backcard_card_text": skill_text(_field(back, "skillCol")),
                "backcard_image_url": _image(back),
                "backcard_card_config": _config(back),
            })
        cards.append(data)
    return cards


def fetch_cardlist(category: str) -> str:
    from curl_cffi import requests as http

    resp = http.post(CARDLIST_URL, data={"category_exp": category}, impersonate="chrome", timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"{resp.status_code} downloading the official card list ({category})")
    return resp.text


def import_set(category: str, page: str | None = None) -> dict:
    """Trae (o actualiza) una colección de la web oficial como cartas provisionales.

    Las que TCG+ ya tiene se saltan: manda TCG+."""
    cards = parse_cardlist(page if page is not None else fetch_cardlist(category))
    if len(cards) < MIN_EXPECTED:
        raise RuntimeError(f"Only {len(cards)} cards in the official list: wrong series or the website changed?")
    numbers = [c["card_number"] for c in cards]
    in_tcgplus = set(Card.objects.filter(card_number__in=numbers, id__lt=CUSTOM_ID_START)
                     .values_list("card_number", flat=True))
    provisional = {c.card_number: c.id for c in Card.objects.filter(id__gte=CUSTOM_ID_START, raw__has_key="official_site")}
    last = Card.objects.filter(id__gte=CUSTOM_ID_START).order_by("-id").values_list("id", flat=True).first()
    next_id = (last or CUSTOM_ID_START) + 1

    items = []
    for data in cards:
        number = data["card_number"]
        if number in in_tcgplus:
            continue
        card_id = provisional.get(number)
        if card_id is None:
            card_id, next_id = next_id, next_id + 1
        data["id"] = card_id
        if "backcard_card_name" in data:
            data["backcard_id"] = card_id  # solo marca que tiene reverso (como en TCG+)
        data["official_site"] = {"category": category, "fetched": date.today().isoformat()}
        items.append(data)

    ids = [d["id"] for d in items]
    before = snapshot_cards(ids)
    created, updated, failed = upsert_cards(items)
    record_card_changes(before, ids)
    invalidate_facets()
    if created or updated:
        from scanner.tasks import build_fingerprints

        build_fingerprints.delay()
    return {"listed": len(cards), "in_tcgplus": len(in_tcgplus), "created": created, "updated": updated,
            "failed": len(failed)}


# --- Cuando llega a TCG+ ------------------------------------------------------------

def _tcgplus_card(card: Card) -> Card | None:
    """La impresión de TCG+ que sustituye a la provisional: la de su misma rareza (la del sobre) o la primera."""
    return (Card.objects.filter(card_number=card.card_number, id__lt=CUSTOM_ID_START)
            .annotate(same=Case(When(rarity_code=card.rarity_code, then=Value(0)), default=Value(1),
                                output_field=IntegerField()))
            .order_by("same", "id").first())


@transaction.atomic
def merge_into(old: Card, new: Card) -> None:
    """Pasa a `new` todo lo que apunta a `old` (sumando copias si ya había) y borra `old`."""
    from collection.models import CollectionEntry, Want
    from decks.models import DeckVersionCard, Match, PickList, SideCard
    from history.models import ActivityItem
    from scanner.models import Scan

    for entry in CollectionEntry.objects.filter(card=old):
        same = CollectionEntry.objects.filter(card=new, location=entry.location, fake=entry.fake).first()
        if same:
            same.quantity += entry.quantity
            same.notes = same.notes or entry.notes
            same.save(update_fields=["quantity", "notes", "updated_at"])
            entry.delete()
        else:
            CollectionEntry.objects.filter(pk=entry.pk).update(card=new)

    want = Want.objects.filter(card=old).first()
    if want:
        mine = Want.objects.filter(card=new).first()
        if mine:
            mine.quantity = min(99, mine.quantity + want.quantity)
            mine.save(update_fields=["quantity", "updated_at"])
            want.delete()
        else:
            Want.objects.filter(pk=want.pk).update(card=new)

    for row in DeckVersionCard.objects.filter(card=old):
        same = DeckVersionCard.objects.filter(version=row.version, card=new, section=row.section).first()
        if same:
            same.quantity += row.quantity
            same.save(update_fields=["quantity"])
            row.delete()
        else:
            DeckVersionCard.objects.filter(pk=row.pk).update(card=new)

    for side in SideCard.objects.filter(card=old):
        same = SideCard.objects.filter(deck=side.deck, card=new).first()
        if same:
            same.quantity += side.quantity
            same.save(update_fields=["quantity"])
            side.delete()
        else:
            SideCard.objects.filter(pk=side.pk).update(card=new)

    Match.objects.filter(opponent_leader_bandai_id=old.id).update(opponent_leader_bandai_id=new.id)
    Scan.objects.filter(matched_card=old).update(matched_card=new)
    ActivityItem.objects.filter(card_id=old.id).update(card_id=new.id)

    for pick in PickList.objects.all():
        changed = False
        for group in pick.groups:
            for card in group.get("cards", []):
                if card.get("bandai_id") == old.id:
                    card["bandai_id"] = new.id
                    changed = True
        done = [f"{k.rsplit('-', 1)[0]}-{new.id}" if k.endswith(f"-{old.id}") else k for k in pick.done]
        if changed or done != pick.done:
            pick.done = done
            pick.save(update_fields=["groups", "done"])

    # La novedad ya se anunció con la provisional: la de TCG+ no es «nueva» otra vez.
    if CardChange.objects.filter(card=old, kind=CardChange.Kind.NEW).exists():
        CardChange.objects.filter(card=new, kind=CardChange.Kind.NEW).delete()
    CardChange.objects.filter(card=old).update(card=new)
    old.delete()  # sus huellas del escáner y sus precios se van con ella


def reconcile() -> dict:
    """Sustituye las cartas provisionales que TCG+ ya publica por las de TCG+."""
    merged = []
    for card in Card.objects.filter(id__gte=CUSTOM_ID_START, raw__has_key="official_site").order_by("id"):
        target = _tcgplus_card(card)
        if target is None:
            continue
        try:
            merge_into(card, target)
            merged.append(card.card_number)
        except Exception:  # noqa: BLE001 - una carta no debe parar las demás
            logger.exception("Could not replace provisional card %s with %s", card.card_number, target.id)
    if merged:
        invalidate_facets()
        logger.info("Replaced %s provisional cards with the TCG+ ones", len(merged))
    return {"merged": len(merged)}
