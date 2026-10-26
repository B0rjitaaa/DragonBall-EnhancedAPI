"""Estado del sistema (/api/health/): cada pieza, si funciona y por qué no.

- Críticas (si falla alguna, el estado es "down" y la respuesta 503): base de datos, Redis,
  el worker de Celery y el del escáner.
- Avisos (estado "degraded", respuesta 200): syncs con Bandai y las listas oficiales que
  llevan demasiado sin actualizarse.
- Opcional (se informa pero no cuenta): la cámara de la estación fija.
"""
from __future__ import annotations

from datetime import timedelta

import requests
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.db.models import Max
from django.utils import timezone

from .models import BanListEntry, CardErrata, CardRuling, SyncRun

SYNC_MAX_AGE = timedelta(days=2)  # cartas nuevas y banlist: a diario
WEEKLY_MAX_AGE = timedelta(days=8)  # erratas y Q&A: los lunes
PING_TIMEOUT = 1.5


def _ago(when) -> str:
    if when is None:
        return "nunca"
    hours = (timezone.now() - when).total_seconds() / 3600
    return f"hace {hours:.0f} h" if hours < 48 else f"hace {hours / 24:.0f} días"


def _database():
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return True, "responde"


def _redis():
    value = timezone.now().isoformat()
    cache.set("health-probe", value, 30)
    ok = cache.get("health-probe") == value
    return ok, "responde" if ok else "no guarda ni devuelve datos"


def _workers() -> dict[str, bool]:
    from config.celery import app

    names = [name for reply in (app.control.ping(timeout=PING_TIMEOUT) or []) for name in reply]
    return {
        "worker": any(n.startswith("celery@") for n in names),
        "scanner_worker": any(n.startswith("scanner@") for n in names),
    }


def _cards_sync():
    last_ok = SyncRun.objects.filter(status__in=[SyncRun.Status.SUCCESS, SyncRun.Status.PARTIAL]) \
        .order_by("-started_at").values_list("finished_at", flat=True).first()
    latest = SyncRun.objects.order_by("-started_at").first()
    ok = last_ok is not None and timezone.now() - last_ok <= SYNC_MAX_AGE
    detail = f"último correcto {_ago(last_ok)}"
    if latest is not None and latest.status == SyncRun.Status.FAILED:
        ok = False
        detail += f"; el último falló: {latest.error[:120]}"
    return ok, detail


def _official(model, max_age):
    fetched = model.objects.aggregate(last=Max("fetched_at"))["last"]
    ok = fetched is not None and timezone.now() - fetched <= max_age
    return ok, f"actualizada {_ago(fetched)}"


def _camera():
    if not settings.CAMERA_URL:
        return None, "no configurada"
    try:
        response = requests.get(f"{settings.CAMERA_URL}/health", timeout=2)
    except requests.RequestException:
        return False, "el servicio de cámara no responde"
    if response.ok:
        return True, "webcam conectada"
    return False, "sin webcam conectada (la estación fija es opcional)"


CHECKS = [
    # clave, nombre, tipo, función
    ("database", "Base de datos", "critical", _database),
    ("redis", "Redis (caché y colas)", "critical", _redis),
    ("worker", "Worker de Celery", "critical", None),
    ("scanner_worker", "Worker del escáner", "critical", None),
    ("cards_sync", "Sync de cartas con Bandai", "warning", _cards_sync),
    ("banlist", "Banlist oficial", "warning", lambda: _official(BanListEntry, SYNC_MAX_AGE)),
    ("errata", "Erratas oficiales", "warning", lambda: _official(CardErrata, WEEKLY_MAX_AGE)),
    ("rulings", "Card Q&A oficial", "warning", lambda: _official(CardRuling, WEEKLY_MAX_AGE)),
    ("camera", "Cámara de la estación fija", "optional", _camera),
]


def system_health() -> dict:
    try:
        workers = _workers()
        workers_error = None
    except Exception as exc:  # noqa: BLE001 - sin broker no hay forma de preguntar a los workers
        workers, workers_error = {}, f"no se pudo preguntar: {exc}"

    checks = []
    for key, label, kind, func in CHECKS:
        if func is None:  # workers: ya preguntados de una vez
            ok = workers.get(key, False)
            detail = workers_error or ("responde" if ok else "no responde")
        else:
            try:
                ok, detail = func()
            except Exception as exc:  # noqa: BLE001 - una comprobación rota cuenta como fallo
                ok, detail = False, f"error: {exc}"[:200]
        checks.append({"key": key, "label": label, "kind": kind, "ok": ok, "detail": detail})

    if any(c["kind"] == "critical" and not c["ok"] for c in checks):
        status = "down"
    elif any(c["kind"] == "warning" and not c["ok"] for c in checks):
        status = "degraded"
    else:
        status = "ok"
    return {"status": status, "checked_at": timezone.now(), "checks": checks}
