"""Manejador de logging que guarda los errores en ErrorGroup (lo usan el servidor y Celery).

Cualquier `logger.error(...)` / `logger.exception(...)` acaba aquí, también los 500 que
anota Django (logger `django.request`) y las tareas que fallan (Celery anota el error).
Guardar un error nunca debe romper nada: si la BD no responde, se descarta en silencio.
Se carga con la configuración de logging, antes que los modelos: los importa al usarse.
"""
from __future__ import annotations

import logging
import threading
import traceback as tb
from pathlib import Path

_busy = threading.local()


def _where(exc_tb) -> str:
    """El sitio del código propio más cercano al error (fichero:línea en función)."""
    from django.conf import settings

    frames = tb.extract_tb(exc_tb)
    base = str(settings.BASE_DIR)
    own = [f for f in frames if f.filename.startswith(base) and "site-packages" not in f.filename]
    frame = (own or frames or [None])[-1]
    if frame is None:
        return ""
    path = Path(frame.filename)
    name = str(path.relative_to(base)) if frame.filename.startswith(base) else path.name
    return f"{name}:{frame.lineno} in {frame.name}"


class DatabaseHandler(logging.Handler):
    """Manejador de logging que guarda los errores (nivel ERROR o más) en ErrorGroup."""

    def __init__(self, source: str = "server", level=logging.ERROR):
        super().__init__(level)
        self.source = source

    def emit(self, record: logging.LogRecord) -> None:
        # Un error al guardar el error no vuelve a entrar aquí.
        if getattr(_busy, "on", False) or record.name.startswith("errorlog"):
            return
        _busy.on = True
        try:
            from django.db import connection

            from .recorder import record_error

            # Con la transacción de la petición rota no se puede escribir: se descarta.
            if connection.in_atomic_block and connection.needs_rollback:
                return
            message = record.getMessage()
            request = getattr(record, "request", None)
            if record.exc_info and record.exc_info[0]:
                exc_type, exc, exc_tb = record.exc_info
                kind = exc_type.__name__
                where = _where(exc_tb)
                trace = "".join(tb.format_exception(exc_type, exc, exc_tb))
                if str(exc) and str(exc) not in message:
                    message = f"{message}\n{exc}"
            else:
                # Sin excepción, la causa es el texto sin los datos (la plantilla del mensaje).
                kind, trace = record.name, ""
                where = f"{Path(record.pathname).name} in {record.funcName} · {record.msg}"[:300]
            record_kwargs = {}
            if request is not None and hasattr(request, "get_full_path"):
                record_kwargs = {
                    "request": f"{request.method} {request.get_full_path()}",
                    "user_agent": request.META.get("HTTP_USER_AGENT", ""),
                }
            record_error(self.source, kind, message, where, trace, **record_kwargs)
        except Exception:  # noqa: BLE001
            pass
        finally:
            _busy.on = False
