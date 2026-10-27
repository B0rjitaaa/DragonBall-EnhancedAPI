"""Errores que pasan en el servidor, en las tareas de Celery y en la web, agrupados por causa."""
from django.db import models
from django.utils import timezone


class ErrorGroup(models.Model):
    """Un mismo error (misma causa y mismo sitio): cuántas veces ha pasado y los datos de la última."""

    class Source(models.TextChoices):
        SERVER = "server", "Servidor (API y admin)"
        WORKER = "worker", "Tareas (Celery)"
        WEB = "web", "Web (navegador)"

    # Huella de la causa: el tipo de error y el sitio del código donde salta (no el mensaje,
    # que cambia con los datos). Los que comparten huella son el mismo error.
    signature = models.CharField(max_length=64, unique=True)
    source = models.CharField(max_length=8, choices=Source.choices, db_index=True)
    kind = models.CharField("tipo", max_length=200)
    message = models.TextField("mensaje")
    where = models.CharField("dónde", max_length=300, blank=True)
    traceback = models.TextField("traza", blank=True)
    request = models.CharField("petición", max_length=500, blank=True, help_text="Método y dirección, o la página de la web")
    user_agent = models.CharField("navegador", max_length=300, blank=True)
    count = models.PositiveIntegerField("veces", default=1)
    first_seen = models.DateTimeField("primera vez", default=timezone.now)
    last_seen = models.DateTimeField("última vez", default=timezone.now, db_index=True)
    resolved_at = models.DateTimeField("resuelto", null=True, blank=True)

    class Meta:
        ordering = ["-last_seen"]
        verbose_name = "error"
        verbose_name_plural = "errores"

    def __str__(self):
        return f"{self.kind}: {self.message[:80]}"
