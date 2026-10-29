"""Lista actual de un mazo, versiones congeladas, diferencias y estadísticas."""
from collections import defaultdict

from django.db import transaction
from django.db.models import Max

from cards.models import Card
from collection.models import CollectionEntry, Location, StatusChange

from .models import DeckVersion, DeckVersionCard, Match, SideCard

Section = DeckVersionCard.Section


def section_of(card: Card) -> str:
    return Section.Z if (card.card_type or "").upper().startswith("Z-") else Section.MAIN


def current_list(deck: Location) -> dict[tuple[int, str], int]:
    """{(card_id, sección): copias} de lo que hay ahora en el mazo (también las falsas)."""
    totals: dict[int, int] = defaultdict(int)
    cards: dict[int, Card] = {}
    for entry in CollectionEntry.objects.filter(location=deck).select_related("card"):
        totals[entry.card_id] += entry.quantity
        cards[entry.card_id] = entry.card
    side = dict(SideCard.objects.filter(deck=deck).values_list("card_id", "quantity"))
    out: dict[tuple[int, str], int] = {}
    for card_id, n in totals.items():
        s = min(side.get(card_id, 0), n)
        if s:
            out[(card_id, Section.SIDE)] = s
        if n - s:
            out[(card_id, section_of(cards[card_id]))] = n - s
    return out


def version_list(version: DeckVersion) -> dict[tuple[int, str], int]:
    return {(c.card_id, c.section): c.quantity for c in version.cards.all()}


def latest_version(deck: Location) -> DeckVersion | None:
    return deck.deck_versions.order_by("-number").first()


def save_version(deck: Location, name: str = "", notes: str = "", automatic: bool = False,
                 listing: dict[tuple[int, str], int] | None = None) -> DeckVersion:
    """Guarda una lista del mazo como versión nueva: `listing` o, sin ella, lo que hay ahora en la caja.

    Si coincide con lo que hay en la caja (side incluido), pasa a ser la principal.
    """
    with transaction.atomic():
        Location.objects.select_for_update().filter(pk=deck.pk).first()
        current = current_list(deck)
        listing = current if listing is None else {k: n for k, n in listing.items() if n > 0}
        number = (deck.deck_versions.aggregate(m=Max("number"))["m"] or 0) + 1
        version = DeckVersion.objects.create(deck=deck, number=number, name=name, notes=notes, automatic=automatic)
        DeckVersionCard.objects.bulk_create(
            DeckVersionCard(version=version, card_id=card_id, section=section, quantity=n)
            for (card_id, section), n in listing.items()
        )
        if listing == current:
            make_principal(version)
    return version


def principal_version(deck: Location) -> DeckVersion | None:
    return deck.deck_versions.filter(principal=True).first()


def make_principal(version: DeckVersion) -> None:
    DeckVersion.objects.filter(deck=version.deck, principal=True).exclude(pk=version.pk).update(principal=False)
    if not version.principal:
        version.principal = True
        version.save(update_fields=["principal"])


def version_for_match(deck: Location) -> DeckVersion:
    """La versión con la que se juega: la principal; si aún no hay, la lista que hay en la caja."""
    principal = principal_version(deck)
    if principal is not None:
        return principal
    last = latest_version(deck)
    if last is not None and version_list(last) == current_list(deck):
        make_principal(last)
        return last
    return save_version(deck, automatic=True)


def diff(old: dict, new: dict) -> list[dict]:
    """Cartas añadidas (+) y quitadas (−) entre dos listas, por sección."""
    changes = []
    for key in sorted(set(old) | set(new)):
        delta = new.get(key, 0) - old.get(key, 0)
        if delta:
            changes.append({"card_id": key[0], "section": key[1], "delta": delta})
    return changes


def set_side(deck: Location, card: Card, quantity: int) -> int:
    """Copias de esa carta del mazo que van al side (no más de las que hay)."""
    have = sum(CollectionEntry.objects.filter(location=deck, card=card).values_list("quantity", flat=True))
    quantity = max(0, min(quantity, have))
    if quantity:
        SideCard.objects.update_or_create(deck=deck, card=card, defaults={"quantity": quantity})
    else:
        SideCard.objects.filter(deck=deck, card=card).delete()
    return quantity


def record(matches) -> dict:
    """Victorias, derrotas y empates de unas partidas, y su porcentaje de victorias."""
    w = l = d = 0
    for m in matches:
        w += m.result == Match.Result.WIN
        l += m.result == Match.Result.LOSS
        d += m.result == Match.Result.DRAW
    played = w + l + d
    return {"played": played, "wins": w, "losses": l, "draws": d, "win_rate": round(w / played, 3) if played else None}


def by_leader(matches) -> list[dict]:
    groups: dict[tuple, list] = defaultdict(list)
    for m in matches:
        groups[(m.opponent_leader_bandai_id, m.opponent_leader_name)].append(m)
    rows = [{"leader_bandai_id": k[0], "leader_name": k[1], **record(v)} for k, v in groups.items()]
    return sorted(rows, key=lambda r: (-r["played"], r["leader_name"]))


# --- Hacer principal una versión: mover las copias físicas ----------------------------------


def _wanted(listing: dict[tuple[int, str], int]) -> dict[int, int]:
    """Copias de cada carta que tiene que haber en la caja con esa lista (mazo, Z y side)."""
    wanted: dict[int, int] = defaultdict(int)
    for (card_id, _section), n in listing.items():
        wanted[card_id] += n
    return wanted


def _in_deck(deck: Location) -> dict[int, dict[bool, int]]:
    """{card_id: {fake: copias}} de lo que hay ahora en el mazo."""
    have: dict[int, dict[bool, int]] = defaultdict(lambda: {False: 0, True: 0})
    for card_id, fake, n in CollectionEntry.objects.filter(location=deck).values_list("card_id", "fake", "quantity"):
        have[card_id][fake] += n
    return have


def _source_rank(loc: Location) -> tuple:
    # Primero «Sin ubicar», luego archivadores/almacén/otros y, en último lugar, otros mazos.
    return (not loc.is_default, loc.kind == Location.Kind.DECK, loc.position, loc.name)


def restore_plan(deck: Location, listing: dict[tuple[int, str], int]) -> dict:
    """Qué copias salen de la caja del mazo y cuáles entran (y de dónde) para que tenga esa lista.

    Salen primero las copias falsas; entran primero las auténticas.
    """
    wanted = _wanted(listing)
    have = _in_deck(deck)
    outgoing, incoming = [], []
    for card_id in sorted(set(wanted) | set(have)):
        now = have[card_id][False] + have[card_id][True] if card_id in have else 0
        delta = wanted.get(card_id, 0) - now
        if delta < 0:
            fakes = min(have[card_id][True], -delta)
            outgoing.append({"card_id": card_id, "quantity": -delta, "fakes": fakes})
        elif delta > 0:
            entries = (
                CollectionEntry.objects.filter(card_id=card_id).exclude(location=deck).select_related("location")
            )
            by_loc: dict[int, dict] = {}
            for e in entries:
                row = by_loc.setdefault(e.location_id, {"location": e.location, "authentic": 0, "fakes": 0})
                row["fakes" if e.fake else "authentic"] += e.quantity
            sources = sorted(by_loc.values(), key=lambda r: _source_rank(r["location"]))
            available = sum(r["authentic"] + r["fakes"] for r in sources)
            incoming.append({
                "card_id": card_id, "quantity": delta, "sources": sources,
                "missing": max(0, delta - available),
            })
    side = {card_id: n for (card_id, section), n in listing.items() if section == Section.SIDE}
    return {"outgoing": outgoing, "incoming": incoming, "side": side}


def restore_version(version: DeckVersion, default_target: Location, targets: dict[int, Location] | None = None,
                    sources: dict[int, Location] | None = None) -> dict:
    """Hace principal `version`: mueve las copias para que el mazo tenga exactamente esa lista.

    Lo que sobra va a `targets[card_id]` (o a `default_target`); lo que falta se trae de
    `sources[card_id]` primero y, si no llega, del resto de ubicaciones (ver `_source_rank`).
    Devuelve las copias que no se han encontrado en ninguna parte.
    """
    from collection.services import move_copies

    targets, sources = targets or {}, sources or {}
    deck = version.deck
    missing: dict[int, int] = {}
    with transaction.atomic():
        Location.objects.select_for_update().filter(pk=deck.pk).first()
        plan = restore_plan(deck, version_list(version))
        cards = Card.objects.in_bulk({r["card_id"] for r in plan["outgoing"] + plan["incoming"]})
        for row in plan["outgoing"]:
            card, target = cards[row["card_id"]], targets.get(row["card_id"], default_target)
            if target.pk == deck.pk:
                raise ValueError("The leftover copies cannot stay in the same deck")
            fakes = row["fakes"]
            if fakes:
                move_copies(card, deck, target, fakes, source_fake=True)
            if row["quantity"] - fakes:
                move_copies(card, deck, target, row["quantity"] - fakes, source_fake=False)
        for row in plan["incoming"]:
            card, need = cards[row["card_id"]], row["quantity"]
            preferred = sources.get(row["card_id"])
            ordered = sorted(row["sources"], key=lambda r: (preferred is None or r["location"].pk != preferred.pk,))
            for src in ordered:
                for fake in (False, True):
                    n = min(need, src["fakes" if fake else "authentic"])
                    if n:
                        move_copies(card, src["location"], deck, n, source_fake=fake, target_fake=fake)
                        need -= n
            if need:
                missing[card.pk] = need
        SideCard.objects.filter(deck=deck).delete()
        for card_id, n in plan["side"].items():
            set_side(deck, Card.objects.get(pk=card_id), n)
        make_principal(version)
    return {
        "moved_out": sum(r["quantity"] for r in plan["outgoing"]),
        "moved_in": sum(r["quantity"] for r in plan["incoming"]) - sum(missing.values()),
        "missing": missing,
    }


def history_preview(deck: Location) -> list[dict]:
    """Las copias que hay ahora en el mazo, como irían a «Sin ubicar» al pasarlo al histórico."""
    rows = (
        CollectionEntry.objects.filter(location=deck)
        .select_related("card")
        .order_by("card__card_number", "card_id", "fake")
    )
    return [
        {
            "bandai_id": e.card_id, "card_number": e.card.card_number, "name": e.card.name,
            "card_type": e.card.card_type, "image": e.card.image_url, "quantity": e.quantity, "fake": e.fake,
        }
        for e in rows
    ]


def move_to_history(deck: Location) -> list[dict]:
    """Pasa el mazo al histórico: guarda su lista como versión (para no perder qué llevaba) y
    lleva todas sus copias a «Sin ubicar». Devuelve las copias movidas."""
    from django.utils import timezone

    from collection.services import move_copies

    with transaction.atomic():
        Location.objects.select_for_update().filter(pk=deck.pk).first()
        moved = history_preview(deck)
        if moved:
            save_version(deck, name="When moved to archive", automatic=True)
        target = Location.default()
        for entry in CollectionEntry.objects.filter(location=deck).select_related("card"):
            move_copies(entry.card, deck, target, entry.quantity, source_fake=entry.fake)
        # El side describe la caja, que ahora está vacía (la versión guardada lo conserva).
        SideCard.objects.filter(deck=deck).delete()
        deck.status = Location.Status.PARKED
        deck.parked_at = timezone.now()
        deck.save(update_fields=["status", "parked_at"])
        StatusChange.objects.create(location=deck, status=deck.status, at=deck.parked_at,
                                    copies=sum(c["quantity"] for c in moved))
    return moved


def back_in_use(deck: Location) -> dict | None:
    """Vuelve a usar un mazo del histórico y trae a su caja una copia de su líder (el de su última
    lista), para que el mazo tenga cara; el resto se recupera restaurando esa versión.
    Devuelve la copia que entra ({card…, from, fake}) o None si no hay líder o no tienes ninguna."""
    from django.utils import timezone

    from collection.services import move_copies

    with transaction.atomic():
        Location.objects.select_for_update().filter(pk=deck.pk).first()
        deck.status = Location.Status.ACTIVE
        deck.parked_at = None
        deck.save(update_fields=["status", "parked_at"])
        StatusChange.objects.create(location=deck, status=deck.status, at=timezone.now())
        version = latest_version(deck)
        leader = version and version.cards.filter(card__card_type="LEADER").select_related("card").first()
        if not leader or CollectionEntry.objects.filter(location=deck, card=leader.card).exists():
            return None
        sources = CollectionEntry.objects.filter(card=leader.card).exclude(location=deck).select_related("location")
        source = min(sources, key=lambda e: (e.fake, _source_rank(e.location)), default=None)
        if source is None:
            return None
        move_copies(leader.card, source.location, deck, 1, source_fake=source.fake)
    card = leader.card
    return {"card_number": card.card_number, "name": card.name, "from": source.location.name, "fake": source.fake}
