from concurrent.futures import ThreadPoolExecutor, as_completed

from django.core.management.base import BaseCommand

from cards import thumbs
from cards.models import Card
from collection.models import CollectionEntry


class Command(BaseCommand):
    help = "Genera las miniaturas que falten (primero las de las cartas de Mi colección)."

    def add_arguments(self, parser):
        parser.add_argument("--collection-only", action="store_true", help="Solo las cartas de Mi colección")
        parser.add_argument("--workers", type=int, default=2)

    def handle(self, *args, collection_only: bool, workers: int, **options):
        owned = set(CollectionEntry.objects.values_list("card_id", flat=True))
        cards = Card.objects.exclude(image_url="")
        if collection_only:
            cards = cards.filter(id__in=owned)
        pending = [
            (card_id, url)
            for card_id, url in sorted(cards.values_list("id", "image_url"), key=lambda c: (c[0] not in owned, c[0]))
            if not thumbs.thumb_path(card_id, url).exists()
        ]
        self.stdout.write(f"Miniaturas pendientes: {len(pending)}")
        ok = errors = 0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(thumbs.make_thumb, card_id, url) for card_id, url in pending]
            for done, future in enumerate(as_completed(futures), 1):
                try:
                    future.result()
                    ok += 1
                except Exception:  # noqa: BLE001 - una imagen rota no para el lote
                    errors += 1
                if done % 500 == 0:
                    self.stdout.write(f"  {done}/{len(pending)} ({errors} errores)")
        self.stdout.write(self.style.SUCCESS(f"Miniaturas: {ok} generadas, {errors} errores"))
