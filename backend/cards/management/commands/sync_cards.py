from django.core.management.base import BaseCommand

from cards.tasks import sync_cards


class Command(BaseCommand):
    help = "Syncs with the Bandai TCG+ API (only new cards by default)."

    def add_arguments(self, parser):
        parser.add_argument("--full", action="store_true", help="Download all cards again")
        parser.add_argument("--async", dest="run_async", action="store_true",
                            help="Queue it in Celery instead of running it here")

    def handle(self, *args, full, run_async, **options):
        if run_async:
            result = sync_cards.delay(full=full)
            self.stdout.write(f"Queued: {result.id}")
        else:
            self.stdout.write(str(sync_cards(full=full)))
