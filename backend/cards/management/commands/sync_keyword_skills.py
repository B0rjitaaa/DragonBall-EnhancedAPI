from django.core.management.base import BaseCommand, CommandError

from cards import skills
from cards.importer import invalidate_facets


class Command(BaseCommand):
    help = "Actualiza las keyword skills oficiales (dbs-cardgame.com) y reclasifica las cartas."

    def add_arguments(self, parser):
        parser.add_argument("--snapshot", action="store_true",
                            help="Cargar la copia incluida en el proyecto en vez de descargarla")

    def handle(self, *args, snapshot, **options):
        if snapshot:
            catalog = skills.Catalog.from_snapshot()
            skills.store_entries(catalog.entries, "Jul. 22, 2022", "snapshot")
            count = skills.recompute_cards(catalog)
            invalidate_facets()
            self.stdout.write(self.style.SUCCESS(f"Copia local cargada; {count} cartas reclasificadas"))
            return
        try:
            result = skills.sync_keyword_skills()
        except Exception as exc:  # noqa: BLE001
            raise CommandError(f"No se pudo actualizar desde la web oficial: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(str(result)))
