"""Las copias de seguridad que deja scripts/backup.sh, vistas desde el backend.

En el servidor, la carpeta de las copias (BACKUP_DIR) se monta en solo lectura:
- last_status.json: cómo acabó la última copia.
- running.json: existe mientras hay una copia en curso.
- daily/, weekly/ y otras carpetas: una subcarpeta por copia (o ficheros sueltos).
Para pedir una copia se deja el fichero `now` en BACKUP_REQUEST_DIR (con escritura).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.utils import timezone

# Grupos conocidos, en este orden; el resto de carpetas van al final como «Otras».
GROUPS = {"daily": "Diarias", "weekly": "Semanales"}
DOWNLOADABLE = (".dump",)


@dataclass
class BackupFile:
    name: str
    path: str  # relativa a BACKUP_DIR
    size: int

    @property
    def downloadable(self) -> bool:
        return self.name.endswith(DOWNLOADABLE)


@dataclass
class Copy:
    name: str
    group: str
    when: datetime | None
    files: list[BackupFile] = field(default_factory=list)

    @property
    def size(self) -> int:
        return sum(f.size for f in self.files)


def backup_dir() -> Path | None:
    return Path(settings.BACKUP_DIR) if settings.BACKUP_DIR else None


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _parse_time(value: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(value) if value else None
    except ValueError:
        return None


def status() -> dict:
    """Estado para la cabecera: configurada, última copia, en curso y si hay una pedida."""
    base = backup_dir()
    if base is None or not base.is_dir():
        return {"configured": False}
    last = _read_json(base / "last_status.json")
    if last:
        last["finished_at"] = _parse_time(last.get("finished_at"))
    running = _read_json(base / "running.json")
    if running:
        running["started_at"] = _parse_time(running.get("started_at"))
    return {
        "configured": True,
        "last": last,
        "running": running,
        "requested": is_requested(),
        "can_request": Path(settings.BACKUP_REQUEST_DIR).is_dir(),
    }


def _when(name: str) -> datetime | None:
    # Las copias llevan la fecha en el nombre, en hora local: AAAA-MM-DD_HHMM (con prefijo o sufijo).
    found = re.search(r"\d{4}-\d{2}-\d{2}_\d{4}", name)
    try:
        return timezone.make_aware(datetime.strptime(found.group(), "%Y-%m-%d_%H%M")) if found else None
    except ValueError:
        return None


def _files(folder: Path, base: Path) -> list[BackupFile]:
    return [
        BackupFile(f.name, str(f.relative_to(base)), f.stat().st_size)
        for f in sorted(folder.rglob("*")) if f.is_file()
    ]


def list_copies() -> list[Copy]:
    """Todas las copias, de la más reciente a la más antigua dentro de cada grupo."""
    base = backup_dir()
    if base is None or not base.is_dir():
        return []
    copies: list[Copy] = []
    folders = sorted(p for p in base.iterdir() if p.is_dir() and p.name != "request")
    folders.sort(key=lambda p: (list(GROUPS).index(p.name) if p.name in GROUPS else len(GROUPS)))
    for folder in folders:
        group = GROUPS.get(folder.name, f"Otras · {folder.name}")
        items = []
        for entry in folder.iterdir():
            if entry.is_dir():
                items.append(Copy(entry.name, group, _when(entry.name), _files(entry, base)))
            elif entry.is_file():  # ficheros sueltos (p. ej. pre-migracion/*.dump): una copia cada uno
                when = _when(entry.name) or datetime.fromtimestamp(entry.stat().st_mtime, tz=timezone.get_current_timezone())
                items.append(Copy(entry.name, group, when, [BackupFile(entry.name, str(entry.relative_to(base)), entry.stat().st_size)]))
        items.sort(key=lambda c: (c.when.timestamp() if c.when else 0, c.name), reverse=True)
        copies.extend(items)
    return copies


def is_requested() -> bool:
    return (Path(settings.BACKUP_REQUEST_DIR) / "now").exists()


def request_backup() -> None:
    """Pide una copia: el servidor la lanza en unos segundos (dbs-backup-request.path)."""
    folder = Path(settings.BACKUP_REQUEST_DIR)
    if not folder.is_dir():
        raise RuntimeError("Este equipo no puede lanzar copias desde aquí")
    (folder / "now").write_text(datetime.now().isoformat(), encoding="utf-8")


def download_path(relative: str) -> Path:
    """La ruta de un fichero descargable dentro de BACKUP_DIR (nada fuera de ella)."""
    base = backup_dir()
    if base is None:
        raise FileNotFoundError(relative)
    path = (base / relative).resolve()
    if not path.is_relative_to(base.resolve()) or not path.is_file() or not path.name.endswith(DOWNLOADABLE):
        raise FileNotFoundError(relative)
    return path
