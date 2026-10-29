"""Ficheros JSON de datos (catálogo y precios), también comprimidos (.json.gz).

Los volcados que van en el repositorio (data/seed/) están comprimidos para que pesen poco; los que rehace el
servidor (data/*.json) no. Al arrancar se usa el más reciente que haya: el del servidor si existe y, si no,
el del repositorio.
"""
from __future__ import annotations

import gzip
import json
import os
import tempfile
from pathlib import Path

from django.core.serializers.json import DjangoJSONEncoder

SEED_DIR = Path("/data/seed")


def read_json(path: str | Path):
    path = Path(path)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: str | Path, data) -> None:
    """Escribe de golpe (a un temporal y luego lo cambia): nunca queda un fichero a medias."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}-", suffix=".tmp")
    os.close(fd)
    try:
        if path.suffix == ".gz":
            # mtime=0: el mismo contenido da el mismo fichero (git no ve cambios si no los hay).
            with open(tmp, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=9, mtime=0) as gz:
                gz.write(json.dumps(data, cls=DjangoJSONEncoder, ensure_ascii=False, separators=(",", ":")).encode())
        else:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(data, fh, cls=DjangoJSONEncoder, ensure_ascii=False, separators=(",", ":"))
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def first_existing(*paths: str | Path | None) -> Path | None:
    for p in paths:
        if p and Path(p).exists():
            return Path(p)
    return None
