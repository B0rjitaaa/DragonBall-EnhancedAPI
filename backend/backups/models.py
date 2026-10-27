from django.db import models


class Backup(models.Model):
    """Sin tabla: solo para que «Copias de seguridad» salga en el admin (ver admin.py).
    Las copias son carpetas que deja scripts/backup.sh en el servidor."""

    class Meta:
        managed = False
        verbose_name = "copia de seguridad"
        verbose_name_plural = "copias de seguridad"
