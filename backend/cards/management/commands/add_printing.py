from django.core.management.base import BaseCommand, CommandError

from cards.models import Card
from cards.printings import add_printing


class Command(BaseCommand):
    help = (
        "Adds a printing that Bandai does not publish (promo, prize…) by cloning another printing of the same card. "
        'E.g.: add_printing 5594 --image https://… --set "Event Pack 09 (Alternate Foil)"'
    )

    def add_arguments(self, parser):
        parser.add_argument("base_id", type=int, help="(Bandai) id of another printing of the same card")
        parser.add_argument("--image", required=True, help="Image URL of this printing")
        parser.add_argument("--set", required=True, dest="card_set", help="Edition, e.g. 'Event Pack 09 (Alternate Foil)'")
        parser.add_argument("--id", type=int, default=None, dest="card_id",
                            help="Custom id (>= 900000000); defaults to the next free one")

    def handle(self, *args, base_id, image, card_set, card_id, **options):
        base = Card.objects.filter(id=base_id).first()
        if base is None:
            raise CommandError(f"Card {base_id} does not exist")
        try:
            card = add_printing(base, image, card_set, card_id)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"{card.card_number} · {card.name} · {card.card_set} → id {card.id}"))
        # Que el escáner la reconozca ya: su huella, a partir de la imagen.
        from scanner.fingerprints import build_pending

        ok, errors = build_pending(card_ids=[card.id])
        if errors:
            self.stdout.write(self.style.WARNING("Could not compute its fingerprint (does the image download?)"))
        else:
            self.stdout.write(f"Scanner fingerprint: {ok}")
