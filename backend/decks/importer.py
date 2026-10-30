"""Importar un mazo de otra web o de una lista en texto, y crearlo con las copias que ya tienes.

Fuentes:
- DeckPlanet (dbs-deckplanet.com/…/deck/<id>): la página trae el mazo en los datos de Next.js (`deckData`).
- Top Deck Diffusion (topdeckdiffusion.com/decks/<id>): la página trae `<script id="export-deck-data">`.
- Time Chamber (time-chamber.net/decks/import?leader=…&main=…&z=…&side=…): la lista va en la dirección.
- Texto: lo que exportan casi todas las webs («4 Jiren, the Avenger [BT14-018]», «4 BT14-018», «BT14-018 x4»),
  con secciones «Leader», «Main Deck», «Z Deck», «Side Deck» opcionales.

Solo se descargan páginas de esas webs conocidas (nada de direcciones arbitrarias). Las cartas se comparan por
número, sin importar la impresión (alt art, promos…) ni los ceros a la izquierda (BT29-086 = BT29-86). Las
copias falsas no cuentan. Primero se usan las copias libres (Sin ubicar, archivadores, cajas) y, de otros mazos,
solo las de los mazos que el usuario acepta: esos mazos guardan una versión nueva con lo que les queda.
"""
from __future__ import annotations

import html
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlparse

from django.db import transaction
from django.db.models import Max

from cards.models import Card
from collection.models import CollectionEntry, Location

from . import services
from .models import DeckVersionCard, PickList

Section = DeckVersionCard.Section
SECTIONS = ("leader", "main", "z", "side")
FETCH_HOSTS = {"dbs-deckplanet.com": "deckplanet", "topdeckdiffusion.com": "topdeckdiffusion"}
SOURCE_LABELS = {"deckplanet": "DeckPlanet", "topdeckdiffusion": "Top Deck Diffusion", "timechamber": "Time Chamber",
                 "text": "a text list"}

# Número de carta: prefijo (BT14, EX23, P, SD16…), guion, dígitos y, a veces, sufijo de impresión (SPR, _PR02, _ALT).
NUMBER = re.compile(r"\b([A-Z]{1,4}\d{0,3})-(\d{1,4})([A-Z_]*\d*)\b", re.I)


class DeckImportError(Exception):
    pass


@dataclass
class ParsedDeck:
    source: str
    name: str = ""
    # (número tal cual, sección: leader / main / z / side, copias)
    lines: list[tuple[str, str, int]] = field(default_factory=list)
    unread: list[str] = field(default_factory=list)


def number_key(number: str) -> tuple[str, int] | None:
    """BT29-086, BT29-86, BT29-086SPR y BT29-86_ALT → ("BT29", 86): la misma carta."""
    m = NUMBER.search(number or "")
    return (m.group(1).upper(), int(m.group(2))) if m else None


# --- Leer la fuente -------------------------------------------------------------------------------------------

def parse_source(source: str) -> ParsedDeck:
    source = (source or "").strip()
    if not source:
        raise DeckImportError("Paste a deck link or a deck list")
    if re.match(r"^https?://", source, re.I) and "\n" not in source:
        return _parse_url(source)
    return parse_text(source)


def _parse_url(url: str) -> ParsedDeck:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().removeprefix("www.")
    if host == "time-chamber.net":
        return _parse_time_chamber(parsed.query)
    site = FETCH_HOSTS.get(host)
    if site is None:
        raise DeckImportError(
            f"Links from {host or 'that site'} can't be read yet. Use the site's export / copy list option and "
            "paste the list as text instead."
        )
    page = _fetch(url)
    return _parse_deckplanet(page) if site == "deckplanet" else _parse_topdeckdiffusion(page)


def _fetch(url: str) -> str:
    from curl_cffi import requests as http

    try:
        resp = http.get(url, impersonate="chrome", timeout=20)
    except Exception as exc:  # red, DNS, certificado…
        raise DeckImportError(f"Couldn't open the link ({exc.__class__.__name__}). Try again or paste the list.") from exc
    if resp.status_code != 200:
        raise DeckImportError(f"The site answered {resp.status_code}: is the deck public?")
    return resp.text


def _parse_deckplanet(page: str) -> ParsedDeck:
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', page, re.S)
    payload = "".join(json.loads(f'"{c}"') for c in chunks)
    start = payload.find('"deckData":')
    if start < 0:
        raise DeckImportError("No deck found on that DeckPlanet page: is it public?")
    data = _json_object(payload, payload.index("{", start))
    deck = ParsedDeck(source="deckplanet", name=str(data.get("deck_name") or "").strip())
    leader = data.get("deck_leader") or {}
    if isinstance(leader, dict) and leader.get("card_number"):
        deck.lines.append((leader["card_number"], "leader", 1))
    for row in (data.get("deck_cards") or []) + (data.get("z_deck_cards") or []):
        card = row.get("card_id") or {}
        zone = str(row.get("zone") or "main").lower()
        section = "z" if zone.startswith("z") else "side" if zone.startswith("side") else "main"
        if card.get("card_number") and row.get("amount_in_deck"):
            deck.lines.append((card["card_number"], section, int(row["amount_in_deck"])))
    return deck


def _json_object(text: str, start: int) -> dict:
    """El objeto JSON que empieza en `start` (equilibrando llaves y respetando las cadenas)."""
    depth, in_string, escaped = 0, False, False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    raise DeckImportError("Couldn't read the deck from that page")


def _parse_topdeckdiffusion(page: str) -> ParsedDeck:
    m = re.search(r'<script id="export-deck-data" type="application/json">\s*(.*?)\s*</script>', page, re.S)
    if not m:
        raise DeckImportError("No deck found on that Top Deck Diffusion page: is it public?")
    data = json.loads(m.group(1))
    title = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S)
    deck = ParsedDeck(source="topdeckdiffusion", name=html.unescape(re.sub(r"<[^>]+>", "", title.group(1))).strip() if title else "")
    leaders = data.get("leaders") or []
    if leaders:  # las dos caras del Leader vienen por separado, con el mismo número
        deck.lines.append((leaders[0]["number"], "leader", 1))
    for key, section in (("main", "main"), ("zdeck", "z"), ("side", "side")):
        for row in data.get(key) or []:
            if row.get("number") and row.get("qty"):
                deck.lines.append((row["number"], section, int(row["qty"])))
    return deck


def _parse_time_chamber(query: str) -> ParsedDeck:
    params = parse_qs(query)
    deck = ParsedDeck(source="timechamber")
    for number in params.get("leader", [])[:1]:
        deck.lines.append((number, "leader", 1))
    for key, section in (("main", "main"), ("z", "z"), ("side", "side")):
        for value in params.get(key, []):
            for item in value.split(","):
                number, _, qty = item.strip().rpartition("x")
                if number and qty.isdigit():
                    deck.lines.append((number, section, int(qty)))
                elif item.strip():
                    deck.unread.append(item.strip())
    if not deck.lines:
        raise DeckImportError("That Time Chamber link has no deck list in it")
    return deck


HEADERS = (
    (re.compile(r"\bleader\b", re.I), "leader"),
    (re.compile(r"\bz[\s-]?deck\b", re.I), "z"),
    (re.compile(r"\bside(\s?deck|board)?\b", re.I), "side"),
    (re.compile(r"\b(main(\s?deck)?|deck)\b", re.I), "main"),
)


def parse_text(text: str) -> ParsedDeck:
    """Una lista en texto: una carta por línea con sus copias, y secciones opcionales."""
    deck = ParsedDeck(source="text")
    section = "main"
    for raw in text.splitlines():
        line = raw.strip().strip("-•*").strip()
        if not line:
            continue
        number = NUMBER.search(line)
        if number is None:
            # Cabecera de sección («_____Leader_____», «## Z Deck», «Side Deck:»…) o línea que no es una carta.
            words = re.sub(r"[^A-Za-z0-9]+", " ", line)  # «_____Leader_____», «## Z Deck:» → palabras
            for pattern, name in HEADERS:
                if pattern.search(words):
                    section = name
                    break
            else:
                deck.unread.append(line)
            continue
        rest = (line[:number.start()] + " " + line[number.end():]).strip()
        qty = re.match(r"^(\d{1,2})\s*[x×]?\b", rest, re.I) or re.search(r"\b[x×]\s*(\d{1,2})$|\b(\d{1,2})\s*[x×]$", rest, re.I)
        n = int(next(g for g in qty.groups() if g)) if qty else 1
        deck.lines.append((number.group(0), section, n))
    if not deck.lines:
        raise DeckImportError("No cards found: each line needs a card number, e.g. “4 BT14-018” or “4 Name [BT14-018]”")
    return deck


# --- Comprobar lo que tienes ----------------------------------------------------------------------------------

@dataclass
class _Card:
    number: str
    ids: list[int]
    primary: int
    name: str
    card_type: str


def _catalog() -> dict[tuple[str, int], _Card]:
    """Índice número → impresiones del catálogo (la impresión «principal»: la de menor id)."""
    out: dict[tuple[str, int], _Card] = {}
    for card_id, number, name, card_type in Card.objects.order_by("id").values_list("id", "card_number", "name", "card_type"):
        key = number_key(number)
        if key is None:
            continue
        entry = out.get(key)
        if entry is None:
            out[key] = _Card(number, [card_id], card_id, name, card_type or "")
        else:
            entry.ids.append(card_id)
    return out


def _requirements(deck: ParsedDeck) -> tuple[dict[tuple[str, int], dict[str, int]], dict[tuple[str, int], _Card], list[str]]:
    """{número: {sección: copias}}, las cartas del catálogo y los números que no existen."""
    catalog = _catalog()
    need: dict[tuple[str, int], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    unknown: list[str] = []
    has_leader = any(section == "leader" for _n, section, _q in deck.lines)
    for number, section, qty in deck.lines:
        key = number_key(number)
        card = catalog.get(key) if key else None
        if card is None:
            unknown.append(number)
            continue
        # Lista sin sección «Leader»: el Leader es la carta de tipo LEADER.
        if not has_leader and section == "main" and card.card_type.upper() == "LEADER":
            section, has_leader, qty = "leader", True, 1
        need[key][section] += qty
    return need, catalog, unknown


def _available(cards: dict[tuple[str, int], _Card], exclude: Location | None = None) -> dict[tuple[str, int], list[dict]]:
    """Copias auténticas de cada número, por ubicación y en orden de preferencia (libres primero, mazos al final)."""
    by_id = {card_id: key for key, card in cards.items() for card_id in card.ids}
    entries = CollectionEntry.objects.filter(card_id__in=by_id, fake=False, quantity__gt=0).select_related("location")
    if exclude is not None:
        entries = entries.exclude(location=exclude)
    out: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for e in entries:
        out[by_id[e.card_id]].append({"location": e.location, "card_id": e.card_id, "quantity": e.quantity,
                                      "notes": e.notes, "position": e.position})
    for rows in out.values():
        rows.sort(key=lambda r: services._source_rank(r["location"]))
    return out


def _allocate(need: dict[str, int], sources: list[dict], take_from: set[int] | None) -> dict:
    """Reparte las copias que pide la lista: primero libres; de mazos, todas (vista previa) o las de `take_from`."""
    total = sum(need.values())
    free, from_decks, picks = 0, defaultdict(int), []
    for src in sources:
        if total <= 0:
            break
        loc = src["location"]
        in_deck = loc.kind == Location.Kind.DECK
        if in_deck and take_from is not None and loc.pk not in take_from:
            continue
        n = min(total, src["quantity"])
        if in_deck:
            from_decks[loc.pk] += n
        else:
            free += n
        picks.append((src["card_id"], loc, n, src))
        total -= n
    return {"free": free, "from_decks": dict(from_decks), "missing": total, "picks": picks}


def _from_free(picks) -> list[dict]:
    """De qué ubicaciones libres salen las copias: [{location, quantity}] (para la vista previa)."""
    out: dict[str, int] = {}
    for _card_id, loc, n, _src in picks:
        if loc.kind != Location.Kind.DECK:
            out[loc.name] = out.get(loc.name, 0) + n
    return [{"location": name, "quantity": n} for name, n in out.items()]


def pick_list(picks: list[tuple[int, Location, int, dict]], cards: dict[int, Card],
              orders: dict[int, dict[int, int]]) -> list[dict]:
    """Dónde coger cada copia, por ubicación (libres primero) y en el orden en que están dentro de ella.

    En cada carta: su puesto en «Mi orden» de la ubicación y las líneas de su nota
    (p. ej. «P. 12 · row 2 · col 3» del modo archivador), para encontrarla en la caja o el archivador.
    """
    by_loc: dict[int, dict] = {}
    for card_id, loc, n, src in picks:
        group = by_loc.setdefault(loc.pk, {"location_id": loc.pk, "location": loc.name, "kind": loc.kind,
                                           "rank": services._source_rank(loc), "cards": []})
        card = cards[card_id]
        group["cards"].append({
            "bandai_id": card_id, "number": card.card_number, "name": card.name, "rarity": card.rarity_code,
            "quantity": n, "position": src["position"] or None,
            "notes": [line for line in (src["notes"] or "").splitlines() if line.strip()],
        })
    ordered = sorted(by_loc.values(), key=lambda g: g.pop("rank"))
    for group in ordered:
        # El puesto de cada carta en «Mi orden» de la ubicación (el orden en que la ves en Mi colección).
        numbered = orders.get(group["location_id"]) or {}
        for c in group["cards"]:
            c["position"] = numbered.get(c["bandai_id"])
        group["cards"].sort(key=lambda c: (c["position"] or 0, number_key(c["number"]) or ("", 0)))
    return ordered


def _order_numbers(location_id: int) -> dict[int, int]:
    """{card_id: puesto 1, 2, 3…} en «Mi orden» de la ubicación (como se ve en Mi colección)."""
    rows = (CollectionEntry.objects.filter(location_id=location_id)
            .order_by("position", "card__card_number", "card_id").values_list("card_id", flat=True))
    out: dict[int, int] = {}
    for card_id in rows:
        out.setdefault(card_id, len(out) + 1)
    return out


def leader_decks(deck: ParsedDeck) -> list[Location]:
    """Mazos en uso que ya tienen el Leader de la lista (cualquier impresión): en la caja o en su lista principal."""
    need, catalog, _unknown = _requirements(deck)
    leader_key = next((key for key, sections in need.items() if "leader" in sections), None)
    if leader_key is None:
        return []
    ids = catalog[leader_key].ids
    in_box = CollectionEntry.objects.filter(card_id__in=ids, location__kind=Location.Kind.DECK).values_list("location_id", flat=True)
    in_list = DeckVersionCard.objects.filter(card_id__in=ids, version__principal=True).values_list("version__deck_id", flat=True)
    return list(Location.objects.filter(pk__in={*in_box, *in_list}, kind=Location.Kind.DECK,
                                        status=Location.Status.ACTIVE).order_by("position", "name"))


def _target_deck(target_id) -> Location | None:
    if target_id in (None, "", 0):
        return None
    target = Location.objects.filter(pk=target_id, kind=Location.Kind.DECK).first()
    if target is None:
        raise DeckImportError("That deck doesn't exist any more")
    return target


def _plan(deck: ParsedDeck, target: Location | None, take_from: set[int] | None):
    """Para cada número: lo que ya está en el mazo destino, lo que entra (libres y mazos aceptados), lo que falta y,
    con un mazo destino, lo que sale de él (lo que no está en la lista nueva) hacia «Sin ubicar».

    `take_from=None` es la vista previa: se cuentan todos los mazos para enseñar qué hay en cada uno.
    """
    need, catalog, unknown = _requirements(deck)
    cards = {key: catalog[key] for key in need}
    available = _available(cards, exclude=target)
    id_key = {card_id: key for key, card in catalog.items() for card_id in card.ids}
    in_target: dict[tuple[str, int], list[dict]] = defaultdict(list)
    leaving: list[dict] = []
    if target is not None:
        for e in CollectionEntry.objects.filter(location=target).select_related("card").order_by("fake", "card_id"):
            row = {"card_id": e.card_id, "fake": e.fake, "quantity": e.quantity, "notes": e.notes, "position": e.position}
            key = id_key.get(e.card_id)
            if key in need:
                in_target[key].append(row)
            else:
                leaving.append(row)
    plans = {}
    for key, sections in need.items():
        want = sum(sections.values())
        kept = []
        for row in in_target.get(key, []):  # primero lo que ya está en el mazo (auténticas antes que falsas)
            n = min(want, row["quantity"])
            if n:
                kept.append((row["card_id"], row["fake"], n))
                want -= n
            if row["quantity"] - n:
                leaving.append({**row, "quantity": row["quantity"] - n})
        plans[key] = {"kept": kept, "alloc": _allocate({"all": want}, available.get(key, []), take_from)}
    return need, cards, plans, available, leaving, unknown


def preview(deck: ParsedDeck, target_id=None) -> dict:
    """Qué cartas de la lista tienes libres, cuáles están en otros mazos y cuáles te faltan; con un mazo destino
    (uno que ya tiene ese Leader), también las que ya están en él y las que saldrían a «Sin ubicar»."""
    target = _target_deck(target_id)
    need, cards, plans, available, leaving, unknown = _plan(deck, target, take_from=None)
    decks = {r["location"].pk: r["location"] for rows in available.values() for r in rows}
    rows, in_use = [], defaultdict(list)
    for key, sections in need.items():
        card, plan = cards[key], plans[key]
        alloc = plan["alloc"]
        rows.append({
            "bandai_id": card.primary, "number": card.number, "name": card.name,
            "sections": {s: sections[s] for s in SECTIONS if sections.get(s)},
            "quantity": sum(sections.values()), "in_deck": sum(n for _c, _f, n in plan["kept"]),
            "free": alloc["free"], "missing": alloc["missing"], "from": _from_free(alloc["picks"]),
            "in_use": [{"deck_id": d, "deck": decks[d].name, "quantity": n} for d, n in alloc["from_decks"].items()],
        })
        for d, n in alloc["from_decks"].items():
            in_use[d].append({"bandai_id": card.primary, "number": card.number, "name": card.name, "quantity": n})
    rows.sort(key=lambda r: (min(SECTIONS.index(s) for s in r["sections"]), number_key(r["number"])))
    names = Card.objects.in_bulk({r["card_id"] for r in leaving})
    grouped: dict[tuple[str, bool], dict] = {}  # una línea por número (las impresiones se juntan) y autenticidad
    for r in leaving:
        card = names[r["card_id"]]
        row = grouped.setdefault((card.card_number, r["fake"]), {"bandai_id": card.pk, "number": card.card_number,
                                                                 "name": card.name, "quantity": 0, "fake": r["fake"]})
        row["quantity"] += r["quantity"]
    out_rows = sorted(grouped.values(), key=lambda r: (number_key(r["number"]) or ("", 0), r["fake"]))
    total = sum(sum(s.values()) for s in need.values())
    return {
        "source": deck.source,
        "source_label": SOURCE_LABELS.get(deck.source, deck.source),
        "name": deck.name,
        "lines": [list(line) for line in deck.lines],
        "rows": rows,
        "has_leader": any("leader" in s for s in need.values()),
        "existing_decks": [{"id": d.pk, "name": d.name} for d in leader_decks(deck)],
        "target": {"id": target.pk, "name": target.name} if target else None,
        "totals": {
            "cards": total,
            "in_deck": sum(r["in_deck"] for r in rows),
            "free": sum(r["free"] for r in rows),
            "in_use": sum(i["quantity"] for r in rows for i in r["in_use"]),
            "missing": sum(r["missing"] for r in rows),
            "leaving": sum(r["quantity"] for r in out_rows),
        },
        "in_use": [{"deck_id": d, "deck": decks[d].name, "cards": items, "copies": sum(i["quantity"] for i in items)}
                   for d, items in in_use.items()],
        "leaving": out_rows,
        "unknown": unknown,
        "unread": deck.unread[:20],
    }


# --- Crear el mazo o añadir la lista ----------------------------------------------------------------------------

def create_deck(deck: ParsedDeck, name: str, take_from: set[int], target_id=None) -> dict:
    """Crea el mazo (o, con `target_id`, guarda la lista como versión nueva de ese mazo) con las copias que tienes:
    las que ya estaban en él, las libres y las de los mazos aceptados. Lo que sobra del mazo va a «Sin ubicar»."""
    from collection.services import move_copies

    target = _target_deck(target_id)
    if target is None:
        name = (name or deck.name or "").strip()[:80]
        if not name:
            raise DeckImportError("Give the deck a name")
        if Location.objects.filter(name__iexact=name).exists():
            raise DeckImportError(f"There's already a location called “{name}”")
    if not _requirements(deck)[0]:
        raise DeckImportError("None of the cards in the list are in the catalog")
    with transaction.atomic():
        if target is None:
            position = (Location.objects.filter(kind=Location.Kind.DECK).aggregate(m=Max("position"))["m"] or 0) + 1
            target = Location.objects.create(name=name, kind=Location.Kind.DECK, position=position)
            created = True
        else:
            Location.objects.select_for_update().filter(pk=target.pk).first()
            created = False
        need, cards, plans, available, leaving, unknown = _plan(deck, target, take_from)
        # «Mi orden» de cada ubicación de origen (y del propio mazo), antes de mover nada: para la lista de recogida.
        orders = {loc_id: _order_numbers(loc_id)
                  for loc_id in {r["location"].pk for rows in available.values() for r in rows} | {target.pk}}
        listing: dict[tuple[int, str], int] = defaultdict(int)
        side_by_card: dict[int, int] = defaultdict(int)
        given: dict[int, dict] = {}
        all_picks: list = []
        moved = missing = 0
        for key, sections in need.items():
            card, plan = cards[key], plans[key]
            # Las copias del mazo, por impresión: las que ya estaban y las que llegan. Se reparten por secciones
            # (Leader/Main/Z primero, side al final).
            pool: list[list[int]] = [[card_id, n] for card_id, _fake, n in plan["kept"]]
            all_picks.extend(plan["alloc"]["picks"])
            for card_id, src, n, _row in plan["alloc"]["picks"]:
                move_copies(Card.objects.get(pk=card_id), src, target, n)
                pool.append([card_id, n])
                moved += n
                if src.kind == Location.Kind.DECK:
                    row = given.setdefault(src.pk, {"deck": src, "copies": 0, "cards": set()})
                    row["copies"] += n
                    row["cards"].add(card_id)
            for section in SECTIONS:
                want = sections.get(section, 0)
                while want and pool:
                    card_id, n = pool[0]
                    take = min(want, n)
                    _add(listing, side_by_card, card_id, section, take, catalog_type=card.card_type)
                    want -= take
                    pool[0][1] -= take
                    if not pool[0][1]:
                        pool.pop(0)
                if want:  # te faltan: entran en la lista con la impresión principal
                    # (solo en la lista: el side de la caja cuenta las copias que hay de verdad)
                    _add(listing, None, card.primary, section, want, catalog_type=card.card_type)
                    missing += want
        # Lo que no está en la lista nueva sale del mazo a «Sin ubicar» (para guardarlo luego donde toque).
        unsorted = Location.default()
        removed = 0
        for row in leaving:
            move_copies(Card.objects.get(pk=row["card_id"]), target, unsorted, row["quantity"], source_fake=row["fake"])
            removed += row["quantity"]
        target.side_cards.all().delete()
        for card_id, n in side_by_card.items():
            services.set_side(target, Card.objects.get(pk=card_id), n)
        bulk = Card.objects.in_bulk({p[0] for p in all_picks} | {r["card_id"] for r in leaving})
        picked = pick_list(all_picks, bulk, orders)
        if leaving:
            picked.append(_out_group(target, leaving, bulk, orders.get(target.pk) or {}))
        PickList.objects.filter(deck=target).delete()
        if picked:
            PickList.objects.create(deck=target, groups=picked)
        source = SOURCE_LABELS.get(deck.source, deck.source)
        version = services.save_version(target, name=f"Imported from {source}", listing=dict(listing))
        services.make_principal(version)
        affected = []
        for row in given.values():
            other = row["deck"]
            for card_id in row["cards"]:  # el side no puede tener más copias de las que quedan
                side = other.side_cards.filter(card_id=card_id).first()
                if side is not None:
                    services.set_side(other, side.card, side.quantity)
            saved = services.save_version(other, name=f"Gave cards to “{target.name}”", automatic=True)
            affected.append({"deck_id": other.pk, "deck": other.name, "copies": row["copies"], "version": saved.number})
    return {
        "deck": {"id": target.pk, "uid": str(target.uid), "name": target.name},
        "created": created,
        "version": version.number,
        "moved": moved,
        "missing": missing,
        "removed": removed,
        "unknown": unknown,
        "decks_changed": affected,
        "pick_list": picked,
    }


def _out_group(deck: Location, leaving: list[dict], cards: dict[int, Card], order: dict[int, int]) -> dict:
    """En la lista de recogida: las copias que salen del mazo a «Sin ubicar» (hay que sacarlas de su caja)."""
    rows = [{
        "bandai_id": r["card_id"], "number": cards[r["card_id"]].card_number, "name": cards[r["card_id"]].name,
        "rarity": cards[r["card_id"]].rarity_code + (" · fake" if r["fake"] else ""), "quantity": r["quantity"],
        "position": order.get(r["card_id"]), "notes": [line for line in (r["notes"] or "").splitlines() if line.strip()],
    } for r in leaving]
    rows.sort(key=lambda c: (c["position"] or 0, number_key(c["number"]) or ("", 0)))
    return {"location_id": deck.pk, "location": f"Take out of “{deck.name}” → Unsorted", "kind": "out", "cards": rows}


def _add(listing, side_by_card, card_id: int, section: str, n: int, catalog_type: str) -> None:
    if section == "side":
        listing[(card_id, Section.SIDE)] += n
        if side_by_card is not None:
            side_by_card[card_id] += n
    elif section == "z" or catalog_type.upper().startswith("Z-"):
        listing[(card_id, Section.Z)] += n
    else:
        listing[(card_id, Section.MAIN)] += n


def parsed_from_lines(lines, source: str = "text", name: str = "") -> ParsedDeck:
    """La lista que devolvió la vista previa (para crear el mazo sin volver a descargar la página)."""
    deck = ParsedDeck(source=source if source in SOURCE_LABELS else "text", name=name)
    for item in lines or []:
        try:
            number, section, qty = str(item[0]), str(item[1]), int(item[2])
        except (TypeError, ValueError, IndexError):
            continue
        if section in SECTIONS and 0 < qty <= 99:
            deck.lines.append((number, section, qty))
    if not deck.lines:
        raise DeckImportError("The deck list is empty")
    return deck
