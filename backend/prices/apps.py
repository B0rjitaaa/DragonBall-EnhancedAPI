from django.apps import AppConfig


class PricesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "prices"
    verbose_name = "Precios (Cardmarket)"

    def ready(self):
        import os

        from celery.signals import worker_ready

        @worker_ready.connect(weak=False)
        def first_prices(**_kwargs):
            # Al arrancar el worker general (no el del escáner): si hay catálogo y aún ningún precio.
            if os.environ.get("SCANNER_WORKER") != "1":
                from .tasks import bootstrap_prices

                bootstrap_prices()
