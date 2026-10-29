from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from cards.importer import upsert_cards
from cards.models import Card
from cards.seed import read_json


class Command(BaseCommand):
    help = "Imports cards from a downloaded JSON file (cartas_dbs.json, or the repo dump .json.gz)."

    def add_arguments(self, parser):
        parser.add_argument("path", nargs="?", default="/data/cartas_dbs.json")
        parser.add_argument("--if-empty", action="store_true",
                            help="Only import if the database has no cards (first start)")

    def handle(self, *args, path, if_empty, **options):
        if if_empty and Card.objects.exists():
            self.stdout.write("The database already has cards: not importing.")
            return
        file = Path(path)
        if not file.exists():
            if if_empty:
                self.stdout.write(f"{file} does not exist: skipping the initial import.")
                return
            raise CommandError(f"{file} does not exist")
        data = read_json(file)
        if isinstance(data, dict):  # por si viene como {"cards": [...]}
            data = data.get("cards") or list(data.values())
        created, updated, errors = upsert_cards(data)
        self.stdout.write(self.style.SUCCESS(
            f"Imported {created + updated} cards ({created} new, {updated} updated)"))
        if errors:
            self.stdout.write(self.style.WARNING(f"{len(errors)} with errors: {errors[:20]}"))
