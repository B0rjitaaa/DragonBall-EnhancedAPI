from django.core.management.base import BaseCommand

from cards.tasks import sync_cards


class Command(BaseCommand):
    help = "Sincroniza con la API de Bandai TCG+ (por defecto solo cartas nuevas)."

    def add_arguments(self, parser):
        parser.add_argument("--full", action="store_true", help="Volver a descargar todas las cartas")
        parser.add_argument("--async", dest="run_async", action="store_true",
                            help="Encolar en Celery en lugar de ejecutar aquí")

    def handle(self, *args, full, run_async, **options):
        if run_async:
            result = sync_cards.delay(full=full)
            self.stdout.write(f"Encolado: {result.id}")
        else:
            self.stdout.write(str(sync_cards(full=full)))
