"""Precios de Cardmarket: su catálogo (expansiones y productos, con la guía de precios del día)
y a qué producto corresponde cada impresión de nuestro catálogo.

Los ficheros públicos de Cardmarket no traen número de carta ni rareza: el emparejamiento se
hace por expansión y nombre (ver matching.py).
"""
from django.db import models

from cards.models import Card


class CardmarketExpansion(models.Model):
    """Una expansión de Cardmarket y el set nuestro (Card.card_set) al que corresponde."""

    id = models.PositiveIntegerField(primary_key=True, help_text="idExpansion de Cardmarket")
    card_set = models.CharField(max_length=255, blank=True, help_text="Set nuestro; vacío = sin emparejar")
    score = models.FloatField(default=0, help_text="Parte de sus nombres que están en ese set (0-1)")
    # Elegida a mano: el emparejamiento diario no la cambia.
    manual = models.BooleanField(default=False)
    # Fusion World va en el mismo juego de Cardmarket, pero no está en nuestro catálogo.
    fusion_world = models.BooleanField(default=False)

    class Meta:
        verbose_name = "expansión de Cardmarket"
        verbose_name_plural = "expansiones de Cardmarket"

    def __str__(self):
        return f"{self.id} → {self.card_set or '—'}"


class CardmarketProduct(models.Model):
    """Una carta suelta de Cardmarket con su precio del día (en euros)."""

    id = models.PositiveIntegerField(primary_key=True, help_text="idProduct de Cardmarket")
    name = models.CharField(max_length=255)
    expansion = models.ForeignKey(CardmarketExpansion, on_delete=models.CASCADE, related_name="products")
    metacard = models.PositiveIntegerField(null=True, blank=True, help_text="Agrupa las impresiones de una carta")
    date_added = models.DateTimeField(null=True, blank=True)
    # Guía de precios del día (None = sin datos).
    trend = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    avg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    low = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    avg1 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    avg7 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    avg30 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    # Precio de referencia (ver cardmarket.reference_price): trend, corregido si se dispara; si
    # no hay, la media de 30 días; y si tampoco (sets recién salidos), el anuncio más barato,
    # marcado con price_is_low porque es menos fiable.
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, db_index=True)
    price_is_low = models.BooleanField(default=False)
    fetched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "producto de Cardmarket"
        verbose_name_plural = "productos de Cardmarket"

    def __str__(self):
        return f"{self.name} ({self.id})"


class CardmarketLink(models.Model):
    """A qué producto de Cardmarket corresponde una impresión nuestra."""

    class Method(models.TextChoices):
        AUTO = "auto", "Automático (única)"
        ORDERED = "ordered", "Automático (por orden)"
        REPRINT = "reprint", "Automático (como su versión normal)"
        MANUAL = "manual", "Elegido a mano"
        NONE = "none", "No está en Cardmarket"
        PRICE = "price", "Precio puesto a mano"

    # Elegidos a mano (producto, «no está» o precio): el emparejamiento diario no los toca.
    MANUAL_METHODS = (Method.MANUAL, Method.NONE, Method.PRICE)

    card = models.OneToOneField(Card, primary_key=True, on_delete=models.CASCADE, related_name="cardmarket")
    # Vacío con method=none (no está en Cardmarket) y method=price (precio puesto a mano).
    product = models.ForeignKey(CardmarketProduct, null=True, blank=True, on_delete=models.CASCADE, related_name="links")
    # Solo con method=price: el precio que puso el usuario (manda sobre el de Cardmarket).
    manual_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    # Precio dudoso: solo un anuncio (sin ventas) y muy por encima de lo que valen las cartas de su
    # rareza (p. ej. un anuncio de relleno a 9.999 €). No cuenta en el valor hasta revisarlo.
    suspect = models.BooleanField(default=False)
    method = models.CharField(max_length=8, choices=Method.choices)

    class Meta:
        verbose_name = "enlace con Cardmarket"
        verbose_name_plural = "enlaces con Cardmarket"

    def __str__(self):
        return f"{self.card_id} → {self.product_id} ({self.method})"


class PriceReview(models.Model):
    """Sin tabla: solo para que «Revisar emparejamientos» salga en el admin (ver admin.py)."""

    class Meta:
        managed = False
        verbose_name = "revisión de emparejamientos"
        verbose_name_plural = "revisar emparejamientos"
