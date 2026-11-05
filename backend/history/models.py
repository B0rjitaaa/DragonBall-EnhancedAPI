"""Histórico de cambios de la colección: cada acción (sumar copias, mover, importar un mazo, restaurar una copia…)
con lo que cambió fila a fila, para verlo y poder deshacerlo. Ver history/recorder.py."""
from django.db import models
from django.utils import timezone


class Activity(models.Model):
    """Una acción del usuario y lo que cambió (sus `items`)."""

    class Source(models.TextChoices):
        WEB = "web", "Web"
        SCANNER = "scanner", "Scanner"
        ADMIN = "admin", "Admin"

    kind = models.CharField(max_length=40, db_index=True)
    title = models.CharField(max_length=300)
    # El título lo dio la acción («Imported deck “…”»); si no, se calcula de lo que cambió (y se recalcula al agrupar).
    custom_title = models.BooleanField(default=False)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.WEB)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    # Última vez que se sumó algo (los clics seguidos sobre la misma carta van a la misma acción).
    updated_at = models.DateTimeField(default=timezone.now)
    # Acciones que se agrupan si van seguidas (p. ej. «adjust:<carta>:<ubicación>»).
    group_key = models.CharField(max_length=200, blank=True)
    undone_at = models.DateTimeField(null=True, blank=True)
    # Si esta acción es un «Undo» (o volver a un punto de restauración): la acción que deshizo.
    undo_of = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="undos")

    class Meta:
        ordering = ["-updated_at", "-id"]
        verbose_name_plural = "activities"

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.title}"


class ActivityItem(models.Model):
    """Una fila que cambió en una acción: cómo estaba antes y cómo quedó (null = no existía / se borró)."""

    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name="items")
    # Qué tabla: entry, location, side, version, version_card, pick_list, status_change, match.
    model = models.CharField(max_length=20)
    key = models.JSONField()
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    # Para filtrar: la carta y la ubicación (o el mazo) a las que afecta.
    card_id = models.IntegerField(null=True, blank=True, db_index=True)
    location_id = models.IntegerField(null=True, blank=True, db_index=True)

    class Meta:
        indexes = [models.Index(fields=["model", "activity"])]


class RestorePoint(models.Model):
    """Foto completa de la colección justo antes de una operación grande (restaurar copia, importar CSV o mazo).

    Se guarda 90 días; «Restore to this point» lo deja todo como estaba en ese momento."""

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    reason = models.CharField(max_length=300)
    activity = models.OneToOneField(Activity, null=True, blank=True, on_delete=models.SET_NULL, related_name="restore_point")
    snapshot = models.JSONField()

    class Meta:
        ordering = ["-created_at"]
