"""Exporta un benchmark fijo de escaneos reales (solo lectura). Deja /tmp/benchmark/ listo.

Elige escaneos confirmados que el modelo acierta usando SOLO huellas oficiales (face=front),
copia sus fotos originales, y guarda el índice de hash (todas las huellas oficiales) y el ORB
solo de los candidatos que identify() pide. Así el test es fiel pero pesa poco.
"""
import json
import os
import shutil

import numpy as np
from django.conf import settings

from scanner.models import CardFingerprint, Scan
from vision.matcher import FingerprintIndex, identify

OUT = "/tmp/benchmark"
IMG_DIR = f"{OUT}/images"
MAX = 18
shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(IMG_DIR)

# Índice de hash con SOLO huellas oficiales (sin las aprendidas de escaneos: evita circularidad)
rows = list(CardFingerprint.objects.filter(face="front").values_list("id", "card_id", "phash", "dhash"))
index = FingerprintIndex.from_rows(rows)
official_cards = set(index.card_ids.tolist())
print(f"Huellas oficiales (front): {len(rows)} | cartas: {len(official_cards)}")

requested: set[int] = set()


def load_orb(ids):
    requested.update(ids)
    return dict(CardFingerprint.objects.filter(id__in=ids).values_list("id", "orb"))


manifest = []
seen_cards: set[int] = set()
candidates_scans = (
    Scan.objects.filter(confirmed=True, dismissed=False)
    .exclude(matched_card_id=None).exclude(image="")
    .order_by("id")
)
for s in candidates_scans:
    if len(manifest) >= MAX:
        break
    if s.matched_card_id in seen_cards or s.matched_card_id not in official_cards:
        continue
    try:
        import cv2
        img = cv2.imread(s.image.path)
        if img is None:
            continue
        # Reducir a máx. 800 px: fotos ligeras para el repo (el reconocimiento aguanta de sobra).
        h, w = img.shape[:2]
        scale = min(1.0, 800 / max(h, w))
        if scale < 1.0:
            img = cv2.resize(img, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)
        # top-8 oficial, sin expansión ancha, para acotar el ORB del fixture
        result = identify(img, index, load_orb, hash_threshold=settings.MATCH_HASH_THRESHOLD,
                          orb_candidates=8, orb_wide=8)
    except Exception as exc:  # noqa: BLE001
        print("  salto scan", s.id, exc)
        continue
    if not result.best or result.best.card_id != s.matched_card_id:
        continue  # solo los que acierta con huellas oficiales (sobre la foto ya reducida)
    name = f"{s.matched_card_id}_{s.id}.jpg"
    cv2.imwrite(f"{IMG_DIR}/{name}", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
    manifest.append({"image": name, "card_id": s.matched_card_id,
                     "card_number": s.matched_card.card_number, "confidence": round(result.confidence, 3)})
    seen_cards.add(s.matched_card_id)

print(f"Escaneos en el benchmark: {len(manifest)} | huellas ORB a exportar: {len(requested)}")

# Guardar índice de hash (compacto) y ORB solo de los pedidos
np.savez_compressed(f"{OUT}/hash_index.npz",
                    ids=np.array([r[0] for r in rows], dtype=np.int64),
                    card_ids=np.array([r[1] for r in rows], dtype=np.int64),
                    phashes=np.array([r[2] for r in rows], dtype=np.int64),
                    dhashes=np.array([r[3] for r in rows], dtype=np.int64))
orb = dict(CardFingerprint.objects.filter(id__in=requested).values_list("id", "orb"))
np.savez_compressed(f"{OUT}/orb.npz", **{str(k): np.frombuffer(v, dtype=np.uint8) for k, v in orb.items()})
json.dump(manifest, open(f"{OUT}/manifest.json", "w"), ensure_ascii=False, indent=1)

import subprocess
sz = subprocess.check_output(["du", "-sh", OUT]).decode().split()[0]
print(f"Benchmark listo en {OUT} ({sz}): {len(manifest)} fotos, hash_index.npz, orb.npz, manifest.json")
