"""Guarda un error en ErrorGroup (sumando una vez si ya existía) y avisa de los nuevos."""
from __future__ import annotations

import hashlib

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from .models import ErrorGroup


def signature(source: str, kind: str, where: str) -> str:
    return hashlib.sha256(f"{source}|{kind}|{where}".encode()).hexdigest()


def record_error(source: str, kind: str, message: str, where: str = "", traceback: str = "",
                 request: str = "", user_agent: str = "") -> ErrorGroup | None:
    """Suma una vez al error (o lo crea). Si es nuevo, o vuelve tras darlo por resuelto, avisa."""
    now = timezone.now()
    sig = signature(source, kind, where)
    details = {
        "message": message[:5000], "traceback": traceback[:20000], "request": request[:500],
        "user_agent": user_agent[:300], "last_seen": now,
    }
    with transaction.atomic():
        group = ErrorGroup.objects.select_for_update().filter(signature=sig).first()
        if group is None:
            try:
                with transaction.atomic():
                    group = ErrorGroup.objects.create(
                        signature=sig, source=source, kind=kind[:200], where=where[:300], first_seen=now, **details
                    )
            except IntegrityError:  # otro proceso lo acaba de crear
                return record_error(source, kind, message, where, traceback, request, user_agent)
            news = "nuevo"
        else:
            news = "vuelve" if group.resolved_at else None
            ErrorGroup.objects.filter(pk=group.pk).update(count=F("count") + 1, resolved_at=None, **details)
    if news:
        _notify(group.pk, news)
    return group


def _notify(group_id: int, news: str) -> None:
    from django.conf import settings

    from .tasks import notify_error

    if not settings.TELEGRAM_BOT_TOKEN:
        return
    try:
        # Sin reintentos: si Redis no responde, mejor sin aviso que una petición colgada.
        notify_error.apply_async((group_id, news), retry=False, ignore_result=True)
    except Exception:  # noqa: BLE001
        pass
