#!/usr/bin/env python3
"""Vigilante externo: avisa por Telegram si el servidor cae de una forma que él
mismo no puede avisar. Se ejecuta en otro equipo (el de respaldo) cada 5 minutos por cron.

Dentro del servidor, la tarea cards.tasks.check_health avisa de casi todo, pero necesita a
Redis y al worker de Celery. Este script cubre justo lo que ella no ve:
- El servidor no responde (apagado, sin red, nginx parado).
- La web responde pero el backend no (Django caído).
- Redis o el worker de Celery caídos (según /api/health/).

Igual que dentro: aviso si sigue fallando 10 minutos, una sola vez, y otro al arreglarse.
Solo usa la biblioteca estándar de Python 3.

Uso (crontab -e):
  */5 * * * * /usr/bin/python3 /home/USUARIO/dbs-watchdog/watchdog.py /home/USUARIO/dbs-watchdog/watchdog.env

watchdog.env (permisos 600):
  HEALTH_URL=http://192.168.1.50/api/health/
  TELEGRAM_BOT_TOKEN=...
  TELEGRAM_CHAT_ID=...
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

ALERT_AFTER = timedelta(minutes=10)
TIMEOUT = 20

MESSAGES = {
    "server": "El servidor no responde",
    "backend": "El backend no responde (la web carga, pero sin datos)",
    "redis": "Redis caído (escáner y tareas parados)",
    "worker": "Worker de Celery caído (sync y avisos parados)",
}


def load_env(path):
    config = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
    return config


def problems(url):
    """Claves de MESSAGES que fallan ahora mismo, con su detalle."""
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:  # 503: algo crítico caído, el cuerpo dice qué
        body = exc.read()
    except Exception as exc:  # noqa: BLE001 - sin conexión, timeout…
        return {"server": str(exc)[:150]}
    try:
        checks = {c["key"]: c for c in json.loads(body)["checks"]}
    except (ValueError, KeyError, TypeError):  # el 503 de nginx no trae las comprobaciones
        return {"backend": "nginx contesta, Django no"}
    return {k: checks[k]["detail"] for k in ("redis", "worker") if k in checks and not checks[k]["ok"]}


def send(config, text, silent=False):
    data = urllib.parse.urlencode({
        "chat_id": config["TELEGRAM_CHAT_ID"], "text": text, "parse_mode": "HTML",
        "disable_notification": "true" if silent else "false",
    }).encode()
    url = f"https://api.telegram.org/bot{config['TELEGRAM_BOT_TOKEN']}/sendMessage"
    try:
        urllib.request.urlopen(url, data=data, timeout=TIMEOUT).close()
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"Telegram: {exc}", file=sys.stderr)
        return False


def duration(since, now):
    minutes = int((now - since).total_seconds() // 60)
    if minutes < 60:
        return f"{minutes} min"
    if minutes < 48 * 60:
        return f"{minutes // 60} h {minutes % 60:02d} min"
    return f"{minutes // 1440} días"


def escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main():
    env_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "watchdog.env")
    config = load_env(env_path)
    state_path = os.path.join(os.path.dirname(os.path.abspath(env_path)), "watchdog-state.json")
    try:
        with open(state_path, encoding="utf-8") as fh:
            state = json.load(fh)
    except (FileNotFoundError, ValueError):
        state = {}

    now = datetime.now(timezone.utc)
    current = problems(config["HEALTH_URL"])
    if "--test" in sys.argv:
        print(current or "todo en orden")
        sys.exit(0 if send(config, "👀 <b>Vigilante activo</b>\nComprueba el servidor cada 5 minutos.", silent=True) else 1)

    for key, detail in current.items():
        entry = state.setdefault(key, {"since": now.isoformat(), "alerted": False})
        since = datetime.fromisoformat(entry["since"])
        if not entry["alerted"] and now - since >= ALERT_AFTER:
            text = f"🔴 <b>{MESSAGES[key]}</b> desde hace {duration(since, now)}\n{escape(detail)}\n<i>(aviso del vigilante)</i>"
            entry["alerted"] = send(config, text)

    for key in [k for k in state if k not in current]:
        entry = state.pop(key)
        if entry["alerted"]:
            since = datetime.fromisoformat(entry["since"])
            send(config, f"✅ <b>Vuelve a funcionar: {MESSAGES[key]}</b>\nEstuvo fallando {duration(since, now)}.\n<i>(aviso del vigilante)</i>")

    with open(state_path, "w", encoding="utf-8") as fh:
        json.dump(state, fh)


if __name__ == "__main__":
    main()
