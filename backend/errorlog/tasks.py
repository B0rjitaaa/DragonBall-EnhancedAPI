"""Aviso por Telegram de los errores nuevos y limpieza de los resueltos hace tiempo."""
from __future__ import annotations

from datetime import timedelta
from html import escape

from celery import shared_task
from django.utils import timezone

from .models import ErrorGroup

KEEP_RESOLVED = timedelta(days=90)


@shared_task(name="errorlog.tasks.notify_error", ignore_result=True)
def notify_error(group_id: int, news: str) -> bool:
    """Aviso sin sonido la primera vez que aparece un error, o cuando vuelve tras resolverlo."""
    from cards.alerts import send_telegram

    group = ErrorGroup.objects.filter(pk=group_id).first()
    if group is None:
        return False
    title = "🐞 Error nuevo" if news == "nuevo" else "🐞 Vuelve un error resuelto"
    lines = [
        f"<b>{title}</b> · {escape(group.get_source_display())}",
        f"<b>{escape(group.kind)}</b>: {escape(group.message.splitlines()[0][:300] if group.message else '')}",
    ]
    if group.where:
        lines.append(f"<code>{escape(group.where[:200])}</code>")
    if group.request:
        lines.append(escape(group.request[:200]))
    lines.append(f"Detalles: /admin/errorlog/errorgroup/{group.pk}/change/")
    return send_telegram("\n".join(lines), silent=True)


@shared_task(name="errorlog.tasks.purge_resolved_errors")
def purge_resolved_errors() -> int:
    """Borra los errores resueltos hace más de 90 días (si vuelven, se crean de nuevo)."""
    deleted, _ = ErrorGroup.objects.filter(resolved_at__lt=timezone.now() - KEEP_RESOLVED).delete()
    return deleted
