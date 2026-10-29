from django.core.management.base import BaseCommand, CommandError

from cards import rulings
from cards.importer import invalidate_facets


class Command(BaseCommand):
    help = "Updates the official Card Q&A (dbs-cardgame.com) and counts the Q&A per card."

    def add_arguments(self, parser):
        parser.add_argument("--snapshot", action="store_true",
                            help="Load the copy bundled with the project instead of downloading it")

    def handle(self, *args, snapshot, **options):
        if snapshot:
            count = rulings.load_snapshot()
            invalidate_facets()
            self.stdout.write(self.style.SUCCESS(f"Loaded {count} Q&A from the local copy"))
            return
        try:
            result = rulings.sync_rulings()
        except Exception as exc:  # noqa: BLE001
            raise CommandError(f"Could not update from the official website: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(str(result)))
