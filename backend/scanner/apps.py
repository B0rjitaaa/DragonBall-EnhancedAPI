import os

from django.apps import AppConfig


class ScannerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "scanner"
    verbose_name = "Escáner"

    def ready(self):
        from celery.signals import worker_ready

        @worker_ready.connect(weak=False)
        def warm_up(**_kwargs):
            # Solo el worker del escáner (cola «scanner»): el del sync no necesita el índice.
            if os.environ.get("SCANNER_WORKER") == "1":
                from .services import warm_up

                warm_up()
