"""Miniaturas de las imágenes de carta para las cuadrículas.

Las imágenes de Bandai son PNG de ~170 KB a 600 px de ancho; en una cuadrícula se
pintan a ~150 px. Se genera una vez una versión WebP de 320 px (~20-40 KB) a partir
de la caché local de imágenes oficiales (la del escáner) y se guarda junto a ella.

La URL lleva una huella de la imagen original: el navegador la puede guardar para
siempre y, si Bandai cambia la imagen, la URL cambia sola.
"""
from __future__ import annotations

import hashlib
import io
from pathlib import Path

from django.conf import settings
from PIL import Image

WIDTH = 320
QUALITY = 80


def version(image_url: str) -> str:
    return hashlib.sha1(image_url.encode()).hexdigest()[:10]


def thumb_url(card_id: int, image_url: str) -> str:
    return f"/api/thumbs/{card_id}/{version(image_url)}.webp" if image_url else ""


def thumb_path(card_id: int, image_url: str) -> Path:
    return Path(settings.CARD_IMAGES_DIR) / "thumbs" / str(WIDTH) / f"{card_id}-{version(image_url)}.webp"


def make_thumb(card_id: int, image_url: str) -> Path:
    """Ruta de la miniatura, generándola si aún no existe (descarga la imagen si hace falta)."""
    from scanner.images import get_image

    path = thumb_path(card_id, image_url)
    if path.exists():
        return path
    image = Image.open(io.BytesIO(get_image(image_url)))
    image = image.convert("RGBA" if "A" in image.getbands() or image.mode == "P" else "RGB")
    if image.width > WIDTH:
        image = image.resize((WIDTH, round(image.height * WIDTH / image.width)), Image.LANCZOS)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Escritura atómica: dos peticiones a la vez no dejan un fichero a medias.
    tmp = path.with_suffix(f".{id(image)}.part")
    image.save(tmp, "WEBP", quality=QUALITY, method=4)
    tmp.replace(path)
    return path
