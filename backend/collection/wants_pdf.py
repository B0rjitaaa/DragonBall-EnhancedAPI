"""Las wants en PDF (para pasarlas por WhatsApp): hojas A4 con la imagen de cada carta, cuántas copias, su número
y rareza, y el total arriba (sin precios). Se dibuja cada hoja con Pillow y se guardan juntas como PDF."""
from __future__ import annotations

import io
import logging
import re
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# A4 a 150 ppp
PAGE_W, PAGE_H, DPI = 1240, 1754, 150
MARGIN, GAP, COLS, ROWS = 60, 22, 4, 3
HEADER_H, TEXT_H = 130, 124
# 4 × 3 cartas por hoja: el ancho de la carta sale de lo que quepa a lo ancho y a lo alto
CARD_W = min((PAGE_W - 2 * MARGIN - (COLS - 1) * GAP) // COLS,
             int(((PAGE_H - 2 * MARGIN - HEADER_H) // ROWS - GAP - TEXT_H) * 63 / 88))
CARD_H = round(CARD_W * 88 / 63)
GRID_X = (PAGE_W - COLS * CARD_W - (COLS - 1) * GAP) // 2  # la cuadrícula, centrada
INK, MUTED, ACCENT, LINE = (24, 26, 33), (105, 110, 122), (232, 120, 18), (222, 224, 230)
FONTS = Path("/usr/share/fonts/truetype/dejavu")


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype(str(FONTS / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")), size)
    except OSError:  # sin DejaVu (no debería pasar en la imagen): la de Pillow
        return ImageFont.load_default(size=size)


def _fit(draw: ImageDraw.ImageDraw, text: str, font, width: int) -> str:
    """El texto, recortado con «…» si no cabe en `width`."""
    if draw.textlength(text, font=font) <= width:
        return text
    while text and draw.textlength(text + "…", font=font) > width:
        text = text[:-1]
    return text.rstrip() + "…"


def _two_lines(draw: ImageDraw.ImageDraw, text: str, font, width: int) -> list[str]:
    """El nombre en una o dos líneas (la segunda, recortada con «…» si no cabe)."""
    words, first = text.split(), ""
    while words and draw.textlength((first + " " + words[0]).strip(), font=font) <= width:
        first = (first + " " + words.pop(0)).strip()
    if not first:  # una palabra que no cabe sola
        return [_fit(draw, text, font, width)]
    return [first, _fit(draw, " ".join(words), font, width)] if words else [first]


def natural(text: str) -> list:
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", text or "")]


def _card_image(card) -> Image.Image | None:
    from cards.thumbs import make_thumb

    if not card.image_url:
        return None
    try:
        with Image.open(make_thumb(card.id, card.image_url)) as im:
            return im.convert("RGB").resize((CARD_W, CARD_H), Image.LANCZOS)
    except Exception:  # noqa: BLE001 - sin imagen, el hueco con el número
        logger.warning("No image for card %s in the wants PDF", card.id, exc_info=True)
        return None


def render(rows: list[dict], title: str = "My wants") -> bytes:
    """El PDF. `rows`: {card, quantity, eur}, en el orden en que salen (`eur` solo sirve para ordenar)."""
    pages = draw_pages(rows, title)
    out = io.BytesIO()
    pages[0].save(out, "PDF", save_all=True, append_images=pages[1:], resolution=DPI, quality=82)
    return out.getvalue()


def draw_pages(rows: list[dict], title: str = "My wants") -> list[Image.Image]:
    """Las hojas, como imágenes."""
    f_title, f_head, f_name, f_small, f_badge = _font(54, True), _font(26), _font(24, True), _font(21), _font(26, True)
    copies = sum(r["quantity"] for r in rows)
    summary = f"{len(rows)} {'card' if len(rows) == 1 else 'cards'} · {copies} {'copy' if copies == 1 else 'copies'}"

    pages: list[Image.Image] = []

    def new_page(first: bool) -> tuple[Image.Image, ImageDraw.ImageDraw, int]:
        page = Image.new("RGB", (PAGE_W, PAGE_H), "white")
        draw = ImageDraw.Draw(page)
        if first:
            draw.text((MARGIN, MARGIN - 6), title, font=f_title, fill=INK)
            draw.text((MARGIN, MARGIN + 66), summary, font=f_head, fill=MUTED)
            draw.text((PAGE_W - MARGIN, MARGIN + 6), datetime.now().strftime("%d %b %Y"), font=f_head, fill=MUTED, anchor="ra")
            top = MARGIN + HEADER_H
            draw.line((MARGIN, top - 18, PAGE_W - MARGIN, top - 18), fill=LINE, width=2)
        else:
            draw.text((MARGIN, MARGIN - 20), title, font=f_head, fill=MUTED)
            top = MARGIN + 30
        pages.append(page)
        return page, draw, top

    page, draw, top = new_page(True)
    row_h = CARD_H + TEXT_H + GAP
    x_i = y = 0
    y = top
    for r in rows:
        if x_i == COLS:
            x_i, y = 0, y + row_h
        if y + CARD_H + TEXT_H > PAGE_H - MARGIN:
            page, draw, top = new_page(False)
            x_i, y = 0, top
        x = GRID_X + x_i * (CARD_W + GAP)
        card = r["card"]
        image = _card_image(card)
        if image is not None:
            page.paste(image, (x, y))
        else:
            draw.rounded_rectangle((x, y, x + CARD_W, y + CARD_H), radius=12, fill=(240, 241, 245), outline=LINE, width=2)
            draw.text((x + CARD_W / 2, y + CARD_H / 2), card.card_number, font=f_name, fill=MUTED, anchor="mm")
        # Copias: una pastilla naranja en la esquina de la carta
        badge = f"×{r['quantity']}"
        bw = draw.textlength(badge, font=f_badge) + 26
        draw.rounded_rectangle((x + CARD_W - bw - 8, y + 8, x + CARD_W - 8, y + 50), radius=21, fill=ACCENT, outline="white", width=3)
        draw.text((x + CARD_W - 8 - bw / 2, y + 29), badge, font=f_badge, fill="white", anchor="mm")
        ty = y + CARD_H + 8
        for line in _two_lines(draw, card.name, f_name, CARD_W):
            draw.text((x, ty), line, font=f_name, fill=INK)
            ty += 29
        meta = " · ".join(p for p in (card.card_number, card.rarity_code) if p)
        draw.text((x, ty + 4), _fit(draw, meta, f_small, CARD_W), font=f_small, fill=MUTED)
        x_i += 1

    if not rows:
        draw.text((MARGIN, top + 20), "No wants yet.", font=f_head, fill=MUTED)
    total = len(pages)
    for n, p in enumerate(pages, start=1):
        ImageDraw.Draw(p).text((PAGE_W - MARGIN, PAGE_H - 22), f"{n} / {total}", font=f_small, fill=MUTED, anchor="rs")
    return pages
