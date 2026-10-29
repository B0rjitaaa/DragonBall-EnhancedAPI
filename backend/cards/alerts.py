"""Avisos por Telegram cuando algo de /api/health/ falla y cuando vuelve a funcionar.

Lo ejecuta cada 5 minutos la tarea `cards.tasks.check_health` (Celery beat):
- Críticos: se avisa si siguen caídos `ALERT_CRITICAL_AFTER` (10 min), para no avisar
  durante un reinicio o un despliegue. Con sonido.
- Avisos menores (sync, listas oficiales, copia de seguridad): se avisa a la primera,
  sin sonido; ya llevan su propio margen (días u horas) en health.py.
- Cada problema se avisa una sola vez, y otra cuando se arregla.

Lo que esta tarea no puede ver (el servidor apagado, Redis o el worker de Celery caídos) lo vigila
desde fuera, si se configura: un latido a Healthchecks.io (`ping_heartbeat`) o scripts/watchdog.py
en otro equipo de casa.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from html import escape

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .health import system_health

logger = logging.getLogger(__name__)

STATE_KEY = "health-alerts-state"
ALERT_CRITICAL_AFTER = timedelta(minutes=10)


def send_telegram(text: str, silent: bool = False) -> bool:
    """Manda `text` (HTML de Telegram) al chat configurado. False si no hay bot o falla."""
    token, chat = settings.TELEGRAM_BOT_TOKEN, settings.TELEGRAM_CHAT_ID
    if not token or not chat:
        return False
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat, "text": text, "parse_mode": "HTML", "disable_notification": silent},
            timeout=10,
        )
    except requests.RequestException as exc:
        logger.warning("Telegram no responde: %s", exc)
        return False
    if not response.ok:
        logger.warning("Telegram rechazó el aviso: %s %s", response.status_code, response.text[:200])
    return response.ok


def _duration(since: datetime) -> str:
    minutes = int((timezone.now() - since).total_seconds() // 60)
    if minutes < 60:
        return f"{minutes} min"
    if minutes < 48 * 60:
        return f"{minutes // 60} h {minutes % 60:02d} min"
    return f"{minutes // 1440} días"


def ping_heartbeat(report: dict) -> bool:
    """Latido a un vigilante externo (Healthchecks.io o compatible; HEALTHCHECKS_URL). Se manda cada 5 min:
    si deja de llegar (servidor apagado, sin Internet, Celery o Redis caídos), es el servicio externo el que
    avisa. Con algo crítico caído se manda a «/fail» (aviso inmediato). Sin URL, no hace nada."""
    url = settings.HEALTHCHECKS_URL.rstrip("/")
    if not url:
        return False
    down = [c["label"] for c in report["checks"] if c["kind"] == "critical" and c["ok"] is False]
    try:
        response = requests.post(f"{url}/fail" if down else url, data=", ".join(down).encode(), timeout=10)
        return response.ok
    except requests.RequestException:
        logger.warning("No se pudo mandar el latido a %s", url, exc_info=True)
        return False


def check_and_alert() -> list[str]:
    """Compara el estado actual con el de la vez anterior y avisa de los cambios.

    El estado guardado es {clave: {"since": iso, "alerted": bool}} de lo que está fallando.
    Devuelve los avisos enviados (para los logs y los tests).
    """
    now = timezone.now()
    state: dict = cache.get(STATE_KEY) or {}
    sent = []
    failing = set()
    report = system_health()
    ping_heartbeat(report)

    for check in report["checks"]:
        key, kind = check["key"], check["kind"]
        if kind == "optional":
            continue
        if check["ok"] is False:
            failing.add(key)
            entry = state.setdefault(key, {"since": now.isoformat(), "alerted": False})
            since = datetime.fromisoformat(entry["since"])
            due = kind == "warning" or now - since >= ALERT_CRITICAL_AFTER
            if due and not entry["alerted"]:
                icon = "🔴" if kind == "critical" else "🟡"
                extra = f" desde hace {_duration(since)}" if kind == "critical" else ""
                text = f"{icon} <b>{escape(check['label'])}</b>{extra}\n{escape(check['detail'])}"
                if send_telegram(text, silent=kind == "warning"):
                    entry["alerted"] = True
                    sent.append(text)
        elif key in state:
            entry = state.pop(key)
            if entry["alerted"]:
                text = (f"✅ <b>Vuelve a funcionar: {escape(check['label'])}</b>\n"
                        f"Estuvo fallando {_duration(datetime.fromisoformat(entry['since']))}.")
                send_telegram(text, silent=kind == "warning")
                sent.append(text)

    # Lo que ya no se comprueba (o dejó de aplicar) no queda colgado en el estado.
    for key in set(state) - failing:
        state.pop(key)
    cache.set(STATE_KEY, state, None)
    return sent
