from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from cards.models import Card
from prices.models import CardPrice
from prices.snapshot import load, source_file


class Command(BaseCommand):
    help = "Loads prices from a JSON dump (the export_prices one), replacing any existing ones."

    def add_arguments(self, parser):
        parser.add_argument("path", nargs="?", help="Defaults to the server one (data/precios_dbs.json) or the "
                                                         "repository one (data/seed/precios_dbs.json.gz)")
        parser.add_argument("--if-empty", action="store_true",
                            help="Only if there are no prices yet (first start)")

    def handle(self, *args, path, if_empty, **options):
        if if_empty and CardPrice.objects.exists():
            self.stdout.write("Prices already loaded: not importing.")
            return
        file = Path(path) if path else source_file()
        if file is None or not file.exists():
            if if_empty:
                self.stdout.write(f"{file} does not exist: skipping the initial price import.")
                return
            raise CommandError(f"{file} does not exist")
        if not Card.objects.exists():
            if if_empty:
                self.stdout.write("No cards yet: prices will be loaded once the catalog arrives.")
                return
            raise CommandError("No cards: import the catalog first (import_cards or sync_cards).")
        try:
            counts = load(file)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(
            f"Prices imported: {counts['prices.CardPrice']} cards with a price, "
            f"{counts['prices.PricePoint']} history points"))
