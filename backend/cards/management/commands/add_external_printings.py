"""Añade al catálogo, como impresiones propias, versiones vistas en otra web (DeckPlanet) que Bandai no publica.

Lee un JSON [{code, card_number, image, set}]: `set` puede llevar «{base_set}» (la colección de la carta normal),
p. ej. «Pre-Release Stamped · {base_set}». Cada una clona la impresión de Bandai de esa carta (la del sobre, si la
hay), guarda su código de origen para no repetirla y queda marcada como añadida en Tools → Printings review.
"""
import json

from django.core.management.base import BaseCommand
from django.db.models import Case, IntegerField, Value, When
from django.utils import timezone

from cards.models import Card, ExternalPrinting
from cards.printings import CUSTOM_ID_START, add_printing


class Command(BaseCommand):
    help = "Add printings seen on DeckPlanet (JSON list of {code, card_number, image, set}) as custom printings"

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--no-fingerprints", action="store_true", help="Don't compute the scanner fingerprints")

    def handle(self, path, no_fingerprints=False, **opts):
        items = json.load(open(path))
        done = {c.raw.get("deckplanet_code"): c.id for c in Card.objects.filter(id__gte=CUSTOM_ID_START, raw__has_key="deckplanet_code")}
        added, skipped, missing_base = [], 0, []
        for item in items:
            code = item["code"]
            if code in done:
                skipped += 1
                continue
            base = (Card.objects.filter(card_number=item["card_number"], id__lt=CUSTOM_ID_START)
                    .annotate(booster=Case(When(card_set__contains="[DBS-B", then=Value(0)), default=Value(1), output_field=IntegerField()))
                    .order_by("booster", "id").first())
            if base is None:
                missing_base.append(code)
                continue
            card = add_printing(base, item["image"], item["set"].replace("{base_set}", base.card_set))
            card.raw["deckplanet_code"] = code
            card.save(update_fields=["raw"])
            added.append(card.id)
            done[code] = card.id
            ExternalPrinting.objects.filter(source="deckplanet", code=code).update(
                mark=ExternalPrinting.Mark.HAVE, note=f"Added to the catalog (id {card.id})", marked_at=timezone.now())
        self.stdout.write(f"added {len(added)} · already there {skipped} · no base printing {len(missing_base)} {missing_base[:10]}")
        if added and not no_fingerprints:
            from scanner.fingerprints import build_pending

            ok, errors = build_pending(card_ids=added)
            self.stdout.write(f"scanner fingerprints: {ok} ok, {errors} errors")
