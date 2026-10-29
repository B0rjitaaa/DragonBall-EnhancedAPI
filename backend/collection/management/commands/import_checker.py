"""Importa los datos del antiguo escáner (DragonBall-CameraCardChecker).

En el escáner:
    docker compose exec -T backend python manage.py dumpdata cards.card cards.cardfingerprint \
        collection decks scans > escaner.json
Aquí:
    python manage.py import_checker escaner.json
y copiar sus fotos (media/scans/…) al volumen media de aquí, con las mismas rutas.

Las cartas del escáner se cruzan con este catálogo por su id de Bandai (aquí, Card.id).
Si alguna carta de la colección o de un mazo no está en el catálogo no se importa
nada: hay que darla de alta antes (p. ej. con add_printing). Las huellas y escaneos
de cartas que no estén se omiten (se avisa). Mazos, huellas y escaneos son opcionales
en el volcado.
"""
import base64
import json
import uuid
from collections import Counter, defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_date, parse_datetime

from cards.models import Card
from collection.models import CollectionEntry, Location
from decks.models import DeckVersion, DeckVersionCard, Match, SideCard
from scanner.models import CardFingerprint, Scan, ScanSession


class Command(BaseCommand):
    help = "Imports the collection (and decks) from a JSON dump of the scanner"

    def add_arguments(self, parser):
        parser.add_argument("dump", help="`manage.py dumpdata` file from the scanner")
        parser.add_argument("--replace", action="store_true", help="Delete the collection and decks here first")
        parser.add_argument("--dry-run", action="store_true", help="Check the dump without saving anything")

    def handle(self, dump, replace=False, dry_run=False, **options):
        with open(dump, encoding="utf-8") as fh:
            objects = json.load(fh)
        rows: dict[str, list[dict]] = defaultdict(list)
        for obj in objects:
            rows[obj["model"]].append(obj)
        self.stdout.write("Dump: " + ", ".join(f"{m} {len(r)}" for m, r in sorted(rows.items())))

        # Cartas: pk del escáner -> id de Bandai, y que estén todas en este catálogo.
        bandai = {o["pk"]: o["fields"]["bandai_id"] for o in rows["cards.card"]}
        numbers = {o["fields"]["bandai_id"]: o["fields"]["card_number"] for o in rows["cards.card"]}
        used = {o["fields"]["card"] for m in ("collection.collectionentry", "decks.deckversioncard", "decks.sidecard")
                for o in rows[m]}
        if missing_pk := used - set(bandai):
            raise CommandError(f"The dump does not include cards {sorted(missing_pk)} (cards.card is missing)")
        known = set(Card.objects.filter(id__in={bandai[pk] for pk in used}).values_list("id", flat=True))
        if missing := sorted({bandai[pk] for pk in used} - known):
            listing = ", ".join(f"{numbers[b]} ({b})" for b in missing)
            raise CommandError(f"{len(missing)} cards are missing from the catalog: {listing}. Add them first.")

        if not replace and (CollectionEntry.objects.exists() or DeckVersion.objects.exists() or Scan.objects.exists()):
            raise CommandError("There is already a collection, decks or scans here: use --replace to replace them")

        with transaction.atomic():
            if replace:
                Scan.objects.all().delete()
                ScanSession.objects.all().delete()
                if rows["cards.cardfingerprint"]:
                    CardFingerprint.objects.all().delete()
                Match.objects.all().delete()
                DeckVersion.objects.all().delete()
                SideCard.objects.all().delete()
                CollectionEntry.objects.all().delete()
                Location.objects.all().delete()
            counts = self._import(rows, bandai)
            counts.update(self._import_scanner(rows, bandai))
            if dry_run:
                transaction.set_rollback(True)
        verb = "Would import" if dry_run else "Imported"
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
            counts["locations"] += 1

        self.entries: dict[int, CollectionEntry] = {}
        self.locations = locations
        for o in rows["collection.collectionentry"]:
            f = o["fields"]
            entry = self.entries[o["pk"]] = CollectionEntry.objects.create(
                card_id=bandai[f["card"]], location=locations[f["location"]], quantity=f["quantity"],
                fake=f.get("fake", False), position=f.get("position", 0), notes=f.get("notes", ""),
            )
            dates = {k: parse_datetime(f[k]) for k in ("created_at", "updated_at") if f.get(k)}
            if dates:
                CollectionEntry.objects.filter(pk=entry.pk).update(**dates)
            counts["copy rows"] += 1
            counts["copies"] += f["quantity"]

        versions: dict[int, DeckVersion] = {}
        for o in rows["decks.deckversion"]:
            f = o["fields"]
            v = DeckVersion.objects.create(
                deck=locations[f["deck"]], number=f["number"], name=f.get("name", ""), notes=f.get("notes", ""),
                automatic=f.get("automatic", False), principal=f.get("principal", False),
            )
            DeckVersion.objects.filter(pk=v.pk).update(created_at=parse_datetime(f["created_at"]))
            versions[o["pk"]] = v
            counts["deck lists"] += 1
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
            counts["matches"] += 1
        return counts

    def _import_scanner(self, rows, bandai) -> Counter:
        """Sesiones, escaneos y huellas del escáner (las fotos se copian aparte, mismas rutas)."""
        counts = Counter()
        known = set(Card.objects.values_list("id", flat=True))

        def card_id(pk):
            b = bandai.get(pk)
            return b if b in known else None

        sessions: dict[int, ScanSession] = {}
        for o in rows["scans.scansession"]:
            f = o["fields"]
            session = ScanSession.objects.create(
                mode=f.get("mode", "burst"), location=self.locations.get(f.get("location")),
                ended_at=parse_datetime(f["ended_at"]) if f.get("ended_at") else None,
            )
            ScanSession.objects.filter(pk=session.pk).update(started_at=parse_datetime(f["started_at"]))
            sessions[o["pk"]] = session
            counts["sessions"] += 1

        scans: dict[int, Scan] = {}
        for o in rows["scans.scan"]:
            f = dict(o["fields"])
            original = f.pop("matched_card", None)
            matched = card_id(original) if original else None
            if original and matched is None:
                counts["scans with unknown card"] += 1
            session = sessions.get(f.pop("session", None))
            entry = self.entries.get(f.pop("collection_entry", None))
            # Los candidatos guardan el id de carta del escáner: se pasan al de aquí.
            candidates = []
            for cand in f.pop("candidates", []) or []:
                cid = card_id(cand.get("card_id"))
                if cid is not None:
                    candidates.append({**cand, "card_id": cid})
            created_at, finished_at = f.pop("created_at"), f.pop("finished_at", None)
            scan = Scan.objects.create(
                matched_card_id=matched, session=session, collection_entry=entry, candidates=candidates,
                **{k: v for k, v in f.items() if k in {fl.name for fl in Scan._meta.fields}},
            )
            Scan.objects.filter(pk=scan.pk).update(
                created_at=parse_datetime(created_at), finished_at=parse_datetime(finished_at) if finished_at else None,
            )
            scans[o["pk"]] = scan
            counts["scans"] += 1

        prints = []
        for o in rows["cards.cardfingerprint"]:
            f = o["fields"]
            cid = card_id(f["card"])
            if cid is None:
                counts["fingerprints skipped (unknown card)"] += 1
                continue
            prints.append(CardFingerprint(
                card_id=cid, face=f["face"], source_url=f.get("source_url", ""), scan=scans.get(f.get("scan")),
                phash=f["phash"], dhash=f["dhash"], orb=base64.b64decode(f["orb"]), orb_count=f.get("orb_count", 0),
            ))
        CardFingerprint.objects.bulk_create(prints, batch_size=500)
        counts["fingerprints"] += len(prints)
        return counts
