import os

from celery import Celery
from celery.signals import after_setup_logger

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("dbs")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@after_setup_logger.connect
def save_errors(logger, **kwargs):
    # Celery pone sus propios manejadores en los workers: se añade el que guarda los errores en la BD
    # (una sola vez, y apuntados como de las tareas, no del servidor).
    from errorlog.handler import DatabaseHandler

    for handler in [h for h in logger.handlers if isinstance(h, DatabaseHandler)]:
        logger.removeHandler(handler)
    logger.addHandler(DatabaseHandler(source="worker"))
