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
        CHEAPEST = "cheapest", "Automático (la más barata de varias)"
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


class TcgProduct(models.Model):
    """Una carta de TCGplayer (vía tcgcsv.com) con su precio de mercado del día, en dólares."""

    id = models.PositiveIntegerField(primary_key=True, help_text="productId de TCGplayer")
    group_id = models.PositiveIntegerField(db_index=True)
    group_name = models.CharField(max_length=255, blank=True)
    name = models.CharField(max_length=255)
    # Número normalizado (BT20-149) y rareza tal como la escribe TCGplayer ("Secret Rare").
    number = models.CharField(max_length=32, db_index=True, blank=True)
    rarity = models.CharField(max_length=64, blank=True)
    # Lo que va entre paréntesis al final del nombre: "Alternate Art", "SPR", "Silver Foil"…
    variant = models.CharField(max_length=64, blank=True)
    # Precio de mercado (de ventas reales), el más bajo anunciado y la versión (Normal o Foil).
    market_usd = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    low_usd = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sub_type = models.CharField(max_length=16, blank=True)
    fetched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "producto de TCGplayer"
        verbose_name_plural = "productos de TCGplayer"

    def __str__(self):
        return f"{self.name} ({self.id})"


class TcgLink(models.Model):
    """A qué producto de TCGplayer corresponde una impresión nuestra."""

    card = models.OneToOneField(Card, primary_key=True, on_delete=models.CASCADE, related_name="tcgplayer")
    product = models.ForeignKey(TcgProduct, on_delete=models.CASCADE, related_name="links")

    class Meta:
        verbose_name = "enlace con TCGplayer"
        verbose_name_plural = "enlaces con TCGplayer"


class ExchangeRate(models.Model):
    """Cambio del dólar a euros del Banco Central Europeo (1 € = usd_per_eur $)."""

    date = models.DateField(primary_key=True)
    usd_per_eur = models.DecimalField(max_digits=10, decimal_places=4)

    class Meta:
        ordering = ["-date"]
        verbose_name = "cambio dólar/euro"
        verbose_name_plural = "cambios dólar/euro"

    @classmethod
    def latest(cls):
        return cls.objects.first()


class CardPrice(models.Model):
    """El precio de cada carta, ya combinado (ver pricing.py): el que se muestra y cuenta en el valor."""

    class Source(models.TextChoices):
        CARDMARKET = "cardmarket", "Cardmarket"
        TCGPLAYER = "tcgplayer", "TCGplayer"
        MANUAL = "manual", "Puesto a mano"

    card = models.OneToOneField(Card, primary_key=True, on_delete=models.CASCADE, related_name="price")
    eur = models.DecimalField(max_digits=10, decimal_places=2, db_index=True)
    source = models.CharField(max_length=12, choices=Source.choices)
    # Cuenta en el valor de la colección (con ventas, a mano o confirmado).
    counts = models.BooleanField(default=True)
    # Lo que dice cada fuente (en €), para enseñarlo en el detalle.
    cardmarket_eur = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tcgplayer_eur = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "precio de carta"
        verbose_name_plural = "precios de cartas"


class PricePoint(models.Model):
    """Historial: el precio de una carta desde una fecha (solo se guarda cuando cambia)."""

    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name="price_history")
    date = models.DateField(db_index=True)
    eur = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["card", "date"]
        constraints = [models.UniqueConstraint(fields=["card", "date"], name="unique_price_point")]
        verbose_name = "precio histórico"
        verbose_name_plural = "historial de precios"
