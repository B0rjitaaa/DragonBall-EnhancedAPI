"""Desempate entre impresiones hermanas (mismo número, distinta edición: promos, Judge…).

El reconocimiento compara la carta entera y dos hermanas son casi iguales: cambia un sello,
el código del set, la rareza o el borde. Aquí se busca DÓNDE se diferencian las imágenes
oficiales de las hermanas y la foto se compara con cada una solo en esas zonas.

Si las referencias son idénticas (o casi) o ninguna gana con claridad, no se decide: el
escaneo debe ir a "Revisar" para que el usuario elija la edición.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .preprocess import CARD_H, CARD_W

DIFF_THRESHOLD = 40  # diferencia de gris (0-255) para que un píxel cuente como distinto entre hermanas
MIN_DIFF_AREA = 0.002  # fracción de la carta que tiene que diferir; por debajo, referencias idénticas
MARGIN = 0.15  # la mejor tiene que estar al menos un 15 % más cerca que la segunda


@dataclass
class Tiebreak:
    winner: int | None  # índice en `references`, o None si no se puede decidir
    reason: str  # "decided" | "identical" | "close"
    distances: list[float]
    diff_area: float


def _gray(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    gray = cv2.resize(gray, (CARD_W, CARD_H), interpolation=cv2.INTER_AREA)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    return cv2.equalizeHist(gray)  # iguala la luz de la foto con la de la imagen oficial


def difference_mask(references: list[np.ndarray]) -> np.ndarray:
    """Zonas donde las imágenes oficiales de las hermanas no coinciden."""
    stack = np.stack([_gray(r) for r in references]).astype(np.int16)
    spread = (stack.max(axis=0) - stack.min(axis=0)) > DIFF_THRESHOLD
    mask = cv2.morphologyEx(spread.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    # Un poco de holgura: la foto nunca queda alineada al píxel con la referencia.
    return cv2.dilate(mask, np.ones((9, 9), np.uint8)).astype(bool)


def tiebreak(query: np.ndarray, references: list[np.ndarray]) -> Tiebreak:
    """Elige entre `references` (imágenes oficiales de las hermanas) la que es `query`
    (el recorte de la foto). Prueba también la foto girada 180° por si estaba al revés."""
    mask = difference_mask(references)
    area = float(mask.mean())
    if len(references) < 2 or area < MIN_DIFF_AREA:
        return Tiebreak(None, "identical", [], area)

    refs = [_gray(r).astype(np.float32)[mask] for r in references]
    best_distances: list[float] | None = None
    for variant in (query, cv2.rotate(query, cv2.ROTATE_180)):
        q = _gray(variant).astype(np.float32)[mask]
        distances = [float(np.abs(q - r).mean()) for r in refs]
        if best_distances is None or min(distances) < min(best_distances):
            best_distances = distances

    order = np.argsort(best_distances)
    best, second = best_distances[order[0]], best_distances[order[1]]
    if second <= 0 or (second - best) / second < MARGIN:
        return Tiebreak(None, "close", best_distances, area)
    return Tiebreak(int(order[0]), "decided", best_distances, area)
