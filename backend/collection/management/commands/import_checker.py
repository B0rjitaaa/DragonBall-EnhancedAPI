"""Importa los datos del antiguo escáner (DragonBall-CameraCardChecker).

En el escáner:
    docker compose exec -T backend python manage.py dumpdata cards.card collection decks > escaner.json
Aquí:
    python manage.py import_checker escaner.json

Las cartas del escáner se cruzan con este catálogo por su id de Bandai (aquí, Card.id).
Si alguna no está en el catálogo no se importa nada: hay que darla de alta antes
(p. ej. con add_printing). Los mazos (decks.*) son opcionales en el volcado.
"""
import json
import uuid
from collections import Counter, defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_date, parse_datetime

from cards.models import Card
from collection.models import CollectionEntry, Location
from decks.models import DeckVersion, DeckVersionCard, Match, SideCard


class Command(BaseCommand):
    help = "Importa la colección (y los mazos) de un volcado JSON del escáner"

    def add_arguments(self, parser):
        parser.add_argument("dump", help="Fichero de `manage.py dumpdata` del escáner")
        parser.add_argument("--replace", action="store_true", help="Borra antes la colección y los mazos de aquí")
        parser.add_argument("--dry-run", action="store_true", help="Comprueba el volcado sin guardar nada")

    def handle(self, dump, replace=False, dry_run=False, **options):
        with open(dump, encoding="utf-8") as fh:
            objects = json.load(fh)
        rows: dict[str, list[dict]] = defaultdict(list)
        for obj in objects:
            rows[obj["model"]].append(obj)
        self.stdout.write("Volcado: " + ", ".join(f"{m} {len(r)}" for m, r in sorted(rows.items())))

        # Cartas: pk del escáner -> id de Bandai, y que estén todas en este catálogo.
        bandai = {o["pk"]: o["fields"]["bandai_id"] for o in rows["cards.card"]}
        numbers = {o["fields"]["bandai_id"]: o["fields"]["card_number"] for o in rows["cards.card"]}
        used = {o["fields"]["card"] for m in ("collection.collectionentry", "decks.deckversioncard", "decks.sidecard")
                for o in rows[m]}
        if missing_pk := used - set(bandai):
            raise CommandError(f"El volcado no trae las cartas {sorted(missing_pk)} (falta cards.card)")
        known = set(Card.objects.filter(id__in={bandai[pk] for pk in used}).values_list("id", flat=True))
        if missing := sorted({bandai[pk] for pk in used} - known):
            listing = ", ".join(f"{numbers[b]} ({b})" for b in missing)
            raise CommandError(f"Faltan en el catálogo {len(missing)} cartas: {listing}. Dalas de alta antes.")

        if not replace and (CollectionEntry.objects.exists() or DeckVersion.objects.exists()):
            raise CommandError("Ya hay colección o mazos aquí: usa --replace para sustituirlos")

        with transaction.atomic():
            if replace:
                Match.objects.all().delete()
                DeckVersion.objects.all().delete()
                SideCard.objects.all().delete()
                CollectionEntry.objects.all().delete()
                Location.objects.all().delete()
            counts = self._import(rows, bandai)
            if dry_run:
                transaction.set_rollback(True)
        verb = "Se importarían" if dry_run else "Importado"
        self.stdout.write(self.style.SUCCESS(f"{verb}: " + ", ".join(f"{k} {v}" for k, v in counts.items())))

    def _import(self, rows, bandai) -> Counter:
        counts = Counter()
        locations: dict[int, Location] = {}
        for o in sorted(rows["collection.location"], key=lambda o: not o["fields"].get("is_default")):
            f = o["fields"]
            if f.get("is_default"):
                loc = Location.default()
                loc.name, loc.notes, loc.position = f["name"], f.get("notes", ""), f.get("position", 0)
                if f.get("uid"):
                    loc.uid = f["uid"]
                loc.save()
            else:
                loc = Location.objects.create(
                    uid=f.get("uid") or uuid.uuid4(), name=f["name"], kind=f.get("kind", "other"),
                    notes=f.get("notes", ""), position=f.get("position", 0),
                )
            if f.get("created_at"):
                Location.objects.filter(pk=loc.pk).update(created_at=parse_datetime(f["created_at"]))
            locations[o["pk"]] = loc
            counts["ubicaciones"] += 1

        for o in rows["collection.collectionentry"]:
            f = o["fields"]
            entry = CollectionEntry.objects.create(
                card_id=bandai[f["card"]], location=locations[f["location"]], quantity=f["quantity"],
                fake=f.get("fake", False), position=f.get("position", 0), notes=f.get("notes", ""),
            )
            dates = {k: parse_datetime(f[k]) for k in ("created_at", "updated_at") if f.get(k)}
            if dates:
                CollectionEntry.objects.filter(pk=entry.pk).update(**dates)
            counts["filas de copias"] += 1
            counts["copias"] += f["quantity"]

        versions: dict[int, DeckVersion] = {}
        for o in rows["decks.deckversion"]:
            f = o["fields"]
            v = DeckVersion.objects.create(
                deck=locations[f["deck"]], number=f["number"], name=f.get("name", ""), notes=f.get("notes", ""),
                automatic=f.get("automatic", False), principal=f.get("principal", False),
            )
            DeckVersion.objects.filter(pk=v.pk).update(created_at=parse_datetime(f["created_at"]))
            versions[o["pk"]] = v
            counts["listas de mazo"] += 1
        DeckVersionCard.objects.bulk_create(
            DeckVersionCard(version=versions[o["fields"]["version"]], card_id=bandai[o["fields"]["card"]],
                            section=o["fields"]["section"], quantity=o["fields"]["quantity"])
            for o in rows["decks.deckversioncard"]
        )
        SideCard.objects.bulk_create(
            SideCard(deck=locations[o["fields"]["deck"]], card_id=bandai[o["fields"]["card"]],
                     quantity=o["fields"]["quantity"])
            for o in rows["decks.sidecard"]
        )
        for o in rows["decks.match"]:
            f = o["fields"]
            m = Match.objects.create(
                version=versions[f["version"]], played_on=parse_date(f["played_on"]),
                opponent_leader_bandai_id=f.get("opponent_leader_bandai_id"),
                opponent_leader_name=f.get("opponent_leader_name", ""), opponent_name=f.get("opponent_name", ""),
                result=f["result"], went_first=f.get("went_first"), score=f.get("score", ""),
                event=f.get("event", ""), notes=f.get("notes", ""),
            )
            Match.objects.filter(pk=m.pk).update(created_at=parse_datetime(f["created_at"]))
            counts["partidas"] += 1
        return counts
