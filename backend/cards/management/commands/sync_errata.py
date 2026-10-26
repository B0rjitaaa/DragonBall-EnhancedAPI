from django.core.management.base import BaseCommand, CommandError

from cards import errata
from cards.importer import invalidate_facets


class Command(BaseCommand):
    help = "Actualiza las erratas oficiales (dbs-cardgame.com) y marca las cartas."

    def add_arguments(self, parser):
        parser.add_argument("--snapshot", action="store_true",
                            help="Cargar la copia incluida en el proyecto en vez de descargarla")

    def handle(self, *args, snapshot, **options):
        if snapshot:
            count = errata.load_snapshot()
            invalidate_facets()
            self.stdout.write(self.style.SUCCESS(f"Cargadas {count} erratas desde la copia local"))
            return
        try:
            result = errata.sync_errata()
        except Exception as exc:  # noqa: BLE001
            raise CommandError(f"No se pudo actualizar desde la web oficial: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(str(result)))
