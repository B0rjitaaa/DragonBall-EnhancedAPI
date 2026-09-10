import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from cards.importer import upsert_cards
from cards.models import Card


class Command(BaseCommand):
    help = "Importa cartas desde un JSON descargado (p. ej. cartas_dbs.json del script dbs_cards_downloader.py)."

    def add_arguments(self, parser):
        parser.add_argument("path", nargs="?", default="/data/cartas_dbs.json")
        parser.add_argument("--if-empty", action="store_true",
                            help="Solo importar si la base de datos no tiene cartas (arranque inicial)")

    def handle(self, *args, path, if_empty, **options):
        if if_empty and Card.objects.exists():
            self.stdout.write("La base de datos ya tiene cartas: no se importa.")
            return
        file = Path(path)
        if not file.exists():
            if if_empty:
                self.stdout.write(f"No existe {file}: se omite la importación inicial.")
                return
            raise CommandError(f"No existe {file}")
        data = json.loads(file.read_text(encoding="utf-8"))
        if isinstance(data, dict):  # por si viene como {"cards": [...]}
            data = data.get("cards") or list(data.values())
        created, updated, errors = upsert_cards(data)
        self.stdout.write(self.style.SUCCESS(
            f"Importadas {created + updated} cartas ({created} nuevas, {updated} actualizadas)"))
        if errors:
            self.stdout.write(self.style.WARNING(f"{len(errors)} con error: {errors[:20]}"))
