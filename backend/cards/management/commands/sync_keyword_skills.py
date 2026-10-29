from django.core.management.base import BaseCommand, CommandError

from cards import skills
from cards.importer import invalidate_facets


class Command(BaseCommand):
    help = "Updates the official keyword skills (dbs-cardgame.com) and reclassifies the cards."

    def add_arguments(self, parser):
        parser.add_argument("--snapshot", action="store_true",
                            help="Load the copy bundled with the project instead of downloading it")

    def handle(self, *args, snapshot, **options):
        if snapshot:
            catalog = skills.Catalog.from_snapshot()
            skills.store_entries(catalog.entries, "Jul. 22, 2022", "snapshot")
            count = skills.recompute_cards(catalog)
            invalidate_facets()
            self.stdout.write(self.style.SUCCESS(f"Local copy loaded; {count} cards reclassified"))
            return
        try:
            result = skills.sync_keyword_skills()
        except Exception as exc:  # noqa: BLE001
            raise CommandError(f"Could not update from the official website: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(str(result)))
