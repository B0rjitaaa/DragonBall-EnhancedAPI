from django.core.management.base import BaseCommand, CommandError

from cards import banlist


class Command(BaseCommand):
    help = "Actualiza la lista oficial Banned/Limited (dbs-cardgame.com) y marca las cartas."

    def add_arguments(self, parser):
        parser.add_argument("--snapshot", action="store_true",
                            help="Cargar la copia incluida en el proyecto en vez de descargarla")

    def handle(self, *args, snapshot, **options):
        if snapshot:
            count = banlist.load_snapshot()
            self.stdout.write(self.style.SUCCESS(f"Cargadas {count} entradas desde la copia local"))
            return
        try:
            result = banlist.sync_banlist()
        except Exception as exc:  # noqa: BLE001
            raise CommandError(f"No se pudo actualizar desde la web oficial: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(str(result)))
