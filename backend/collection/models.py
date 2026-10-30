"""Mi colección: las copias que tengo de cada carta y dónde están guardadas."""
import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from cards.models import Card

DEFAULT_LOCATION_NAME = "Unsorted"
# Nombre que tenía antes (instalaciones y copias de la colección anteriores).
OLD_DEFAULT_LOCATION_NAME = "Sin ubicar"
# Bolsillos por lado de una página de archivador (hasta 6 × 6).
BINDER_MAX_SIDE = 6


class Location(models.Model):
    """Dónde están guardadas las copias: un mazo, un archivador, una caja…"""

    class Kind(models.TextChoices):
        DECK = "deck", "Deck"
        BINDER = "binder", "Binder"
        STORAGE = "storage", "Storage"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        # Solo cuenta en los mazos: "en el histórico" = ya no lo usas (sus copias pasan a "Sin ubicar").
        ACTIVE = "active", "In use"
        PARKED = "parked", "Archived"

    # Identificador estable para enlaces (/coleccion/mazo/<uid>), que no cambia al renombrar.
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=80, unique=True)
    kind = models.CharField(max_length=8, choices=Kind.choices, default=Kind.OTHER)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ACTIVE)
    parked_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    # Archivadores: bolsillos por página (filas × columnas). Lo usa el escáner en modo archivador.
    binder_rows = models.PositiveSmallIntegerField(
        default=3, validators=[MinValueValidator(1), MaxValueValidator(BINDER_MAX_SIDE)], help_text="Pockets per page: rows"
    )
    binder_cols = models.PositiveSmallIntegerField(
        default=3, validators=[MinValueValidator(1), MaxValueValidator(BINDER_MAX_SIDE)], help_text="Pockets per page: columns"
    )
    # "Sin ubicar": destino por defecto de lo escaneado y de lo que queda al
    # borrar una ubicación. Siempre existe y no se puede borrar.
    is_default = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_default", "position", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["is_default"], condition=models.Q(is_default=True), name="single_default_location"
            ),
        ]

    def __str__(self):
        return self.name

    @classmethod
    def default(cls) -> "Location":
        location, _ = cls.objects.get_or_create(
            is_default=True, defaults={"name": DEFAULT_LOCATION_NAME, "kind": cls.Kind.OTHER}
        )
        return location


class StatusChange(models.Model):
    """Registro de uso de un mazo: cada vez que pasa al histórico o vuelve a usarse."""

    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="status_changes")
    status = models.CharField(max_length=8, choices=Location.Status.choices)
    at = models.DateTimeField(default=timezone.now)
    # Al pasar al histórico: cuántas copias salieron del mazo hacia "Sin ubicar".
    copies = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-at", "-id"]

    def __str__(self):
        return f"{self.location} → {self.status} ({self.at:%Y-%m-%d})"


class CollectionEntry(models.Model):
    """Copias de una carta en una ubicación (las falsas, en su propia fila)."""

    card = models.ForeignKey(Card, on_delete=models.PROTECT, related_name="collection_entries")
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="entries")
    quantity = models.PositiveIntegerField(default=1)
    # Copias falsificadas (p. ej. de AliExpress). Las marca el usuario a mano.
    fake = models.BooleanField(default=False, db_index=True)
    # Orden de la carta dentro de su ubicación ("Mi orden", arrastrando en Mi colección).
    # Las filas auténtica y falsa de una carta en una ubicación comparten posición.
    position = models.PositiveIntegerField(default=0)
    # Detalle dentro de la ubicación (p. ej. "Pág. 12 · fila 2 · col 3").
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["card__card_number", "location", "fake"]
        verbose_name_plural = "collection entries"
        constraints = [
            models.UniqueConstraint(fields=["card", "location", "fake"], name="unique_card_location_fake"),
        ]

    def __str__(self):
        return f"{self.quantity}x {self.card} ({self.location}{', fake' if self.fake else ''})"

    def save(self, *args, **kwargs):
        if self._state.adding and not self.position:
            # Una carta nueva en la ubicación va al final; si ya estaba (la otra fila,
            # auténtica o falsa), en su mismo sitio.
            siblings = CollectionEntry.objects.filter(location_id=self.location_id)
            same = siblings.filter(card_id=self.card_id).values_list("position", flat=True).first()
            self.position = same or (siblings.aggregate(m=models.Max("position"))["m"] or 0) + 1
        super().save(*args, **kwargs)
