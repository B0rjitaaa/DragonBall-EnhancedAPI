"""Escáner: fotos de cartas, su identificación y las huellas con las que se reconocen."""
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from cards.models import Card
from collection.models import BINDER_MAX_SIDE, CollectionEntry, Location


def scan_upload_to(instance, filename):
    # created_at aún no existe cuando se guarda la imagen al crear el Scan.
    return f"scans/{timezone.now():%Y/%m}/{filename}"


class CardFingerprint(models.Model):
    """Huella de una impresión (pHash, dHash y descriptores ORB) para reconocerla en una foto."""

    class Face(models.TextChoices):
        FRONT = "front", "Front"
        BACK = "back", "Back"
        # Foto propia confirmada por el usuario: sirve para impresiones que no
        # están en Bandai TCG+ (promos, premios de torneo) y para afinar el
        # reconocimiento con la cámara e iluminación reales.
        SCAN = "scan", "Confirmed photo"

    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name="fingerprints")
    face = models.CharField(max_length=8, choices=Face.choices, default=Face.FRONT)
    # URL de la imagen oficial a partir de la que se calculó: si cambia, se recalcula.
    source_url = models.URLField(max_length=500, blank=True)
    scan = models.OneToOneField(
        "scanner.Scan", null=True, blank=True, on_delete=models.SET_NULL, related_name="fingerprint"
    )
    phash = models.BigIntegerField()
    dhash = models.BigIntegerField()
    orb = models.BinaryField()
    orb_count = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # Una huella oficial por cara; fotos confirmadas, las que haga falta.
            models.UniqueConstraint(
                fields=["card", "face"],
                condition=~models.Q(face="scan"),
                name="unique_card_face",
            ),
        ]

    def __str__(self):
        return f"{self.card.card_number} ({self.face})"


class ScanSession(models.Model):
    """Sesión de modo ráfaga: el usuario va cambiando cartas bajo la cámara y
    las identificadas con confianza suficiente se añaden solas a la colección."""

    class Mode(models.TextChoices):
        BURST = "burst", "Burst"  # cámara quieta, cada carta nueva se detecta sola
        BINDER = "binder", "Binder"  # carta a carta por las casillas de cada página

    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    mode = models.CharField(max_length=8, choices=Mode.choices, default=Mode.BURST)
    # Dónde entran las cartas que se añaden (vacío = "Sin ubicar").
    location = models.ForeignKey(
        Location, null=True, blank=True, on_delete=models.SET_NULL, related_name="sessions"
    )
    # Modo archivador: bolsillos por página. Si el destino es un archivador, los suyos.
    binder_rows = models.PositiveSmallIntegerField(
        default=3, validators=[MinValueValidator(1), MaxValueValidator(BINDER_MAX_SIDE)]
    )
    binder_cols = models.PositiveSmallIntegerField(
        default=3, validators=[MinValueValidator(1), MaxValueValidator(BINDER_MAX_SIDE)]
    )

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"Session #{self.pk} ({self.started_at:%Y-%m-%d %H:%M})"


class Scan(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    class Source(models.TextChoices):
        UPLOAD = "upload", "Uploaded image"
        CAMERA = "camera", "Camera"

    source = models.CharField(max_length=8, choices=Source.choices, default=Source.UPLOAD)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    image = models.ImageField(upload_to=scan_upload_to, blank=True)
    cropped_image = models.ImageField(upload_to=scan_upload_to, blank=True)
    card_detected = models.BooleanField(default=False)
    matched_card = models.ForeignKey(
        Card, null=True, blank=True, on_delete=models.SET_NULL, related_name="scans"
    )
    confidence = models.FloatField(null=True, blank=True)
    # Confianza por debajo de MATCH_MIN_CONFIDENCE: requiere revisión manual.
    needs_review = models.BooleanField(default=False)
    # El usuario ha confirmado (o corregido) la carta: su recorte se guarda
    # como fingerprint de esa carta.
    confirmed = models.BooleanField(default=False)
    session = models.ForeignKey(
        ScanSession, null=True, blank=True, on_delete=models.SET_NULL, related_name="scans"
    )
    # Modo ráfaga: si se añadió a la colección (y a qué entrada, para deshacer).
    added_to_collection = models.BooleanField(default=False)
    collection_entry = models.ForeignKey(
        CollectionEntry, null=True, blank=True, on_delete=models.SET_NULL, related_name="scans"
    )
    # Copias que suma este escaneo (o sumará al confirmarlo).
    copies = models.PositiveSmallIntegerField(default=1)
    # Descartado: deshecho por el usuario o disparo sin carta (zona vacía).
    dismissed = models.BooleanField(default=False)
    # Lo envía el navegador: ¿quedó vacía la zona desde la captura anterior?
    # Si no, y sale la misma carta que la anterior, lo más probable es que se
    # haya recolocado la misma carta: no se añade sola ("¿Otra copia?").
    after_empty = models.BooleanField(default=True)
    repeat_suspect = models.BooleanField(default=False)
    # Sesión de archivador: página y casilla de la carta (1…filas×columnas de la sesión, por filas).
    binder_page = models.PositiveSmallIntegerField(null=True, blank=True)
    binder_slot = models.PositiveSmallIntegerField(null=True, blank=True)
    # Zona del fotograma a analizar (el marco guía), en fracciones 0-1:
    # {"x", "y", "w", "h"}. Para capturas de la webcam del escáner.
    region = models.JSONField(null=True, blank=True)
    method = models.CharField(max_length=8, blank=True)
    candidates = models.JSONField(default=list, blank=True)
    error = models.TextField(blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Scan #{self.pk} ({self.status})"

    @property
    def binder_position(self) -> str:
        """"P. 12 · row 2 · col 3" (vacío si no es de una sesión de archivador)."""
        if not self.binder_page or not self.binder_slot:
            return ""
        cols = self.session.binder_cols if self.session_id else 3
        row, col = divmod(self.binder_slot - 1, cols)
        return f"P. {self.binder_page} · row {row + 1} · col {col + 1}"
