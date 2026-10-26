"""Benchmark de reconocimiento con escaneos reales (regresiones de la visión).

18 fotos reales ya confirmadas (de la colección, reducidas a 800 px) con la carta
correcta conocida. Se reconocen contra el índice de huellas OFICIALES incluido
(`hash_index.npz` + el ORB de los candidatos en `orb.npz`), sin tocar la BD ni la red.
Si al tocar `vision/` baja el acierto, este test lo detecta.

Regenerar el fixture: scripts/export_benchmark.py en un servidor con datos (ver el
historial de la sesión del 26/10/2026).
"""
import json
from pathlib import Path

import cv2
import numpy as np
from django.conf import settings
from django.test import SimpleTestCase

from vision.matcher import FingerprintIndex, identify

DATA = Path(__file__).parent / "benchmark"
# Todas las fotos elegidas se reconocían bien en las mismas condiciones; exigimos que
# se mantengan (margen de 1 por si alguna queda al límite tras un cambio menor de OpenCV).
MIN_CORRECT_MARGIN = 1


def _load_fixture():
    hi = np.load(DATA / "hash_index.npz")
    index = FingerprintIndex.from_rows(
        zip(hi["ids"].tolist(), hi["card_ids"].tolist(), hi["phashes"].tolist(), hi["dhashes"].tolist())
    )
    orb_npz = np.load(DATA / "orb.npz")
    orb = {int(k): orb_npz[k].tobytes() for k in orb_npz.files}
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    return index, orb, manifest


class BenchmarkTests(SimpleTestCase):
    def test_real_scans_are_recognized(self):
        index, orb, manifest = _load_fixture()

        def load_orb(ids):
            return {i: orb[i] for i in ids if i in orb}

        correct, wrong = 0, []
        for item in manifest:
            img = cv2.imread(str(DATA / "images" / item["image"]))
            self.assertIsNotNone(img, f"no se pudo leer {item['image']}")
            result = identify(img, index, load_orb,
                              hash_threshold=settings.MATCH_HASH_THRESHOLD,
                              orb_candidates=8, orb_wide=8)
            got = result.best.card_id if result.best else None
            if got == item["card_id"]:
                correct += 1
            else:
                wrong.append(f"{item['card_number']}: esperaba {item['card_id']}, obtuvo {got}")

        total = len(manifest)
        self.assertGreaterEqual(
            correct, total - MIN_CORRECT_MARGIN,
            f"Reconocimiento por debajo del mínimo: {correct}/{total}. Fallos:\n" + "\n".join(wrong),
        )
