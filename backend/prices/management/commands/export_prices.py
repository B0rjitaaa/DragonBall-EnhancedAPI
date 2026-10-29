from django.conf import settings
from django.core.management.base import BaseCommand

from prices.snapshot import export


class Command(BaseCommand):
    help = "Vuelca los precios (Cardmarket, TCGplayer, emparejamientos, precios e historial) a un JSON."

    def add_arguments(self, parser):
        parser.add_argument("path", nargs="?", default=settings.PRICES_SNAPSHOT or "/data/precios_dbs.json")

    def handle(self, *args, path, **options):
        counts = export(path)
        self.stdout.write(self.style.SUCCESS(f"Precios volcados en {path}: {sum(counts.values())} filas"))
        for label, n in counts.items():
            self.stdout.write(f"  {label}: {n}")
