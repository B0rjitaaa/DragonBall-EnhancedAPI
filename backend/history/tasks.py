from celery import shared_task

from . import recorder


@shared_task(name="history.tasks.purge_restore_points")
def purge_restore_points() -> int:
    """Borra los puntos de restauración de más de 90 días (el histórico se guarda siempre)."""
    return recorder.purge_restore_points()
