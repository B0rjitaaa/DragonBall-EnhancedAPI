from django.core.management.base import BaseCommand, CommandError

from cards import official_site


class Command(BaseCommand):
    help = ("Imports a set from the official card list (dbs-cardgame.com) that Bandai TCG+ doesn't publish yet, "
            "as provisional cards. The daily sync replaces them with the TCG+ ones when they arrive.")

    def add_arguments(self, parser):
        parser.add_argument("category", nargs="?",
                            help="Series value of the official card list (e.g. 428032 = UB05 CHROMATIC ASCENSION)")
        parser.add_argument("--reconcile", action="store_true",
                            help="Only replace the provisional cards that TCG+ already has")

    def handle(self, *args, category, reconcile, **options):
        if reconcile:
            self.stdout.write(str(official_site.reconcile()))
            return
        if not category:
            raise CommandError("Give the series value (e.g. 428032) or --reconcile")
        try:
            result = official_site.import_set(category)
        except Exception as exc:  # noqa: BLE001
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(str(result)))
