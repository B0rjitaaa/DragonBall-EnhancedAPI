from django.core.management.base import BaseCommand, CommandError

from cards.models import Card
from cards.printings import add_printing


class Command(BaseCommand):
    help = (
        "Añade una impresión que Bandai no publica (promo, premio…) clonando otra de la misma carta. "
        'Ej.: add_printing 5594 --image https://… --set "Event Pack 09 (Alternate Foil)"'
    )

    def add_arguments(self, parser):
        parser.add_argument("base_id", type=int, help="Id (Bandai) de otra impresión de la misma carta")
        parser.add_argument("--image", required=True, help="URL de la imagen de esta impresión")
        parser.add_argument("--set", required=True, dest="card_set", help="Edición, p. ej. 'Event Pack 09 (Alternate Foil)'")
        parser.add_argument("--id", type=int, default=None, dest="card_id",
                            help="Id propio (>= 900000000); por defecto, el siguiente libre")

    def handle(self, *args, base_id, image, card_set, card_id, **options):
        base = Card.objects.filter(id=base_id).first()
        if base is None:
            raise CommandError(f"No existe la carta {base_id}")
        try:
            card = add_printing(base, image, card_set, card_id)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"{card.card_number} · {card.name} · {card.card_set} → id {card.id}"))
