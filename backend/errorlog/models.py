"""Errores que pasan en el servidor, en las tareas de Celery y en la web, agrupados por causa."""
from django.db import models
from django.utils import timezone


class ErrorGroup(models.Model):
    """Un mismo error (misma causa y mismo sitio): cuántas veces ha pasado y los datos de la última."""

    class Source(models.TextChoices):
        SERVER = "server", "Server (API and admin)"
        WORKER = "worker", "Tasks (Celery)"
        WEB = "web", "Web (browser)"

    # Huella de la causa: el tipo de error y el sitio del código donde salta (no el mensaje,
    # que cambia con los datos). Los que comparten huella son el mismo error.
    signature = models.CharField(max_length=64, unique=True)
    source = models.CharField(max_length=8, choices=Source.choices, db_index=True)
    kind = models.CharField("type", max_length=200)
    message = models.TextField("message")
    where = models.CharField("where", max_length=300, blank=True)
    traceback = models.TextField("traceback", blank=True)
    request = models.CharField("request", max_length=500, blank=True, help_text="Method and address, or the web page")
    user_agent = models.CharField("browser", max_length=300, blank=True)
    count = models.PositiveIntegerField("times", default=1)
    first_seen = models.DateTimeField("first seen", default=timezone.now)
    last_seen = models.DateTimeField("last seen", default=timezone.now, db_index=True)
    resolved_at = models.DateTimeField("resolved", null=True, blank=True)

    class Meta:
        ordering = ["-last_seen"]
        verbose_name = "error"
        verbose_name_plural = "errors"

    def __str__(self):
        return f"{self.kind}: {self.message[:80]}"
