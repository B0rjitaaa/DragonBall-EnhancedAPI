from django.core.management.base import BaseCommand

from cards.models import Card
from cards.seed import write_json


class Command(BaseCommand):
    help = "Vuelca el catálogo (registros originales de Bandai, también las impresiones propias) a un JSON (.gz si acaba en .gz)."

    def add_arguments(self, parser):
        parser.add_argument("path", nargs="?", default="/data/seed/cartas_dbs.json.gz")

    def handle(self, *args, path, **options):
        cards = list(Card.objects.order_by("id").values_list("raw", flat=True))
        write_json(path, cards)
        self.stdout.write(self.style.SUCCESS(f"Catálogo volcado en {path}: {len(cards)} cartas"))
