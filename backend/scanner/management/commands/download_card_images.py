from django.core.management.base import BaseCommand

from scanner.images import download_missing
from cards.models import Card


class Command(BaseCommand):
    help = "Downloads the missing official images (front and back) to CARD_IMAGES_DIR."

    def add_arguments(self, parser):
        parser.add_argument("--workers", type=int, default=8)

    def handle(self, *args, workers: int, **options):
        urls = []
        for front, back in Card.objects.values_list("image_url", "back_image_url"):
            urls += [front, back]

        def progress(done, total, errors):
            self.stdout.write(f"  {done}/{total} ({errors} errors)")

        ok, cached, errors = download_missing(urls, workers=workers, progress=progress)
        self.stdout.write(
            self.style.SUCCESS(f"Images: {ok} downloaded, {cached} already cached, {errors} errors")
        )
