from django.core.management.base import BaseCommand, CommandError

from cards import rulings
from cards.importer import invalidate_facets


class Command(BaseCommand):
    help = "Actualiza el Card Q&A oficial (dbs-cardgame.com) y cuenta las Q&A por carta."

    def add_arguments(self, parser):
        parser.add_argument("--snapshot", action="store_true",
                            help="Cargar la copia incluida en el proyecto en vez de descargarla")

    def handle(self, *args, snapshot, **options):
        if snapshot:
            count = rulings.load_snapshot()
            invalidate_facets()
            self.stdout.write(self.style.SUCCESS(f"Cargadas {count} Q&A desde la copia local"))
            return
        try:
            result = rulings.sync_rulings()
        except Exception as exc:  # noqa: BLE001
            raise CommandError(f"No se pudo actualizar desde la web oficial: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(str(result)))
