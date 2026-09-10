from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.db import models


def _array(max_length: int = 64) -> ArrayField:
    return ArrayField(models.CharField(max_length=max_length), default=list, blank=True)


class Legality(models.TextChoices):
    LEGAL = "legal", "Legal"
    LIMITED = "limited", "Limitada"
    BANNED = "banned", "Prohibida"


class Card(models.Model):
    """Una carta (una impresión concreta: las alt-art tienen su propio id en Bandai)."""

    # Identificación
    id = models.PositiveIntegerField(primary_key=True, help_text="ID de Bandai TCG+")
    card_number = models.CharField(max_length=32, db_index=True)
    name = models.CharField(max_length=255, db_index=True)
    text = models.TextField(blank=True)
    image_url = models.URLField(max_length=500, blank=True)

    # Set / expansión (derivado de card_number y card_set)
    card_set = models.CharField(max_length=255, blank=True, db_index=True)
    set_code = models.CharField(max_length=16, blank=True, db_index=True, help_text="BT20, SD1, P, EX01…")
    series = models.CharField(max_length=8, blank=True, db_index=True, help_text="BT, SD, P, EX, TB, DB…")
    set_number = models.PositiveSmallIntegerField(null=True, blank=True)
    collector_number = models.PositiveIntegerField(null=True, blank=True)

    # Atributos normalizados de card_config
    card_type = models.CharField(max_length=32, blank=True, db_index=True)
    colors = _array(16)
    rarity = models.CharField(max_length=64, blank=True)
    rarity_code = models.CharField(max_length=16, blank=True, db_index=True)
    energy = models.SmallIntegerField(null=True, blank=True)
    color_cost = models.CharField(max_length=128, blank=True)
    color_cost_colors = _array(16)
    combo_energy = models.SmallIntegerField(null=True, blank=True)
    combo_power = models.IntegerField(null=True, blank=True)
    power = models.IntegerField(null=True, blank=True)
    z_energy_cost = models.SmallIntegerField(null=True, blank=True)
    characters = _array(128)
    special_traits = _array(128)
    eras = _array(128)
    notes = models.TextField(blank=True)

    # Extraído del texto: [Activate: Main], [Limit 1], [Counter: Play]…
    keywords = _array(96)
    keyword_families = _array(96)  # "Limit 1" -> "Limit", "Counter: Play" -> "Counter"
    regulations = _array(64)

    # Cara trasera (Leaders y cartas de dos caras)
    back_id = models.PositiveIntegerField(null=True, blank=True)
    back_name = models.CharField(max_length=255, blank=True)
    back_text = models.TextField(blank=True)
    back_image_url = models.URLField(max_length=500, blank=True)
    back_power = models.IntegerField(null=True, blank=True)

    # Lista oficial de cartas prohibidas/limitadas (se aplica por card_number, ver banlist.py)
    legality = models.CharField(max_length=8, choices=Legality.choices, default=Legality.LEGAL, db_index=True)
    legality_since = models.CharField(max_length=255, blank=True)

    # Texto normalizado para búsquedas (sin corchetes/HTML, minúsculas). Ver parsing.normalize_search
    effect_text = models.TextField(blank=True, help_text="Texto de ambas caras normalizado")
    search_text = models.TextField(blank=True, help_text="Nombre + número + texto normalizados")

    # Datos originales
    config = models.JSONField(default=dict, blank=True, help_text="card_config original {nombre: valor}")
    back_config = models.JSONField(default=dict, blank=True)
    raw = models.JSONField(default=dict, blank=True, help_text="Respuesta completa de la API")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["series", "set_number", "collector_number", "card_number", "id"]
        indexes = [
            GinIndex(fields=["colors"], name="card_colors_gin"),
            GinIndex(fields=["characters"], name="card_characters_gin"),
            GinIndex(fields=["special_traits"], name="card_traits_gin"),
            GinIndex(fields=["eras"], name="card_eras_gin"),
            GinIndex(fields=["keywords"], name="card_keywords_gin"),
            GinIndex(fields=["keyword_families"], name="card_kwfam_gin"),
            GinIndex(fields=["regulations"], name="card_regulations_gin"),
            GinIndex(fields=["name"], name="card_name_trgm", opclasses=["gin_trgm_ops"]),
            GinIndex(fields=["text"], name="card_text_trgm", opclasses=["gin_trgm_ops"]),
            GinIndex(fields=["effect_text"], name="card_effect_trgm", opclasses=["gin_trgm_ops"]),
            GinIndex(fields=["search_text"], name="card_search_trgm", opclasses=["gin_trgm_ops"]),
            models.Index(fields=["energy"], name="card_energy_idx"),
            models.Index(fields=["power"], name="card_power_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.card_number} {self.name}"

    @property
    def has_back(self) -> bool:
        return self.back_id is not None


class SyncRun(models.Model):
    class Status(models.TextChoices):
        RUNNING = "running", "En curso"
        SUCCESS = "success", "Correcto"
        PARTIAL = "partial", "Con fallos"
        FAILED = "failed", "Error"

    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RUNNING)
    full = models.BooleanField(default=False, help_text="Refrescar todas las cartas, no solo las nuevas")
    listed = models.PositiveIntegerField(default=0)
    fetched = models.PositiveIntegerField(default=0)
    created = models.PositiveIntegerField(default=0)
    updated = models.PositiveIntegerField(default=0)
    failed_ids = models.JSONField(default=list, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"Sync {self.started_at:%Y-%m-%d %H:%M} ({self.status})"


class BanListEntry(models.Model):
    """Una carta de la lista oficial Banned/Limited (dbs-cardgame.com)."""

    card_number = models.CharField(max_length=32, primary_key=True)
    status = models.CharField(max_length=8, choices=[(Legality.LIMITED, "Limitada"), (Legality.BANNED, "Prohibida")])
    card_name = models.CharField(max_length=255, blank=True)
    limit = models.PositiveSmallIntegerField(default=0, help_text="Copias permitidas (limitadas)")
    since = models.CharField(max_length=255, blank=True, help_text="Desde cuándo (Norteamérica/Europa)")
    list_updated = models.CharField(max_length=64, blank=True, help_text="'last updated on …' de la web oficial")
    source = models.CharField(max_length=16, default="official", help_text="official | snapshot")
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["status", "card_number"]
        verbose_name = "Carta prohibida/limitada"
        verbose_name_plural = "Lista Banned/Limited"

    def __str__(self) -> str:
        return f"{self.card_number} ({self.status})"
