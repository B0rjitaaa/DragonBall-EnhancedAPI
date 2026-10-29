from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from cards.models import Card
from prices.models import CardPrice
from prices.snapshot import load, source_file


class Command(BaseCommand):
    help = "Carga los precios de un volcado JSON (el de export_prices), sustituyendo los que hubiera."

    def add_arguments(self, parser):
        parser.add_argument("path", nargs="?", help="Por defecto, el del servidor (data/precios_dbs.json) o el "
                                                         "del repositorio (data/seed/precios_dbs.json.gz)")
        parser.add_argument("--if-empty", action="store_true",
                            help="Solo si aún no hay precios (arranque inicial)")

    def handle(self, *args, path, if_empty, **options):
        if if_empty and CardPrice.objects.exists():
            self.stdout.write("Ya hay precios: no se importan.")
            return
        file = Path(path) if path else source_file()
        if file is None or not file.exists():
            if if_empty:
                self.stdout.write(f"No existe {file}: se omite la importación inicial de precios.")
                return
            raise CommandError(f"No existe {file}")
        if not Card.objects.exists():
            if if_empty:
                self.stdout.write("Aún no hay cartas: los precios se cargarán al llegar el catálogo.")
                return
            raise CommandError("No hay cartas: importa antes el catálogo (import_cards o sync_cards).")
        try:
            counts = load(file)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(
            f"Precios importados: {counts['prices.CardPrice']} cartas con precio, "
            f"{counts['prices.PricePoint']} puntos de historial"))
