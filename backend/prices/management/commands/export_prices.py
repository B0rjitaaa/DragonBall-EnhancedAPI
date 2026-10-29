from django.conf import settings
from django.core.management.base import BaseCommand

from prices.snapshot import export


class Command(BaseCommand):
    help = "Dumps prices (Cardmarket, TCGplayer, matches, prices and history) to a JSON file."

    def add_arguments(self, parser):
        parser.add_argument("path", nargs="?", default=settings.PRICES_SNAPSHOT or "/data/precios_dbs.json")

    def handle(self, *args, path, **options):
        counts = export(path)
        self.stdout.write(self.style.SUCCESS(f"Prices dumped to {path}: {sum(counts.values())} rows"))
        for label, n in counts.items():
            self.stdout.write(f"  {label}: {n}")
