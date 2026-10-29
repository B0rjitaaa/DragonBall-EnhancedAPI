"""Versiones de lista de un mazo y las partidas jugadas con cada una.

Un mazo es una ubicación de tipo «mazo» de la colección; lo que hay en esa
ubicación (copias auténticas y falsas) son las cartas que están físicamente en
su caja. Cada versión es una lista guardada; una de ellas es la principal: la
que está (o debería estar) en la caja y con la que se anotan las partidas.
"""
from django.db import models

from cards.models import Card
from collection.models import Location


class SideCard(models.Model):
    """Cuántas de las copias de una carta que hay en el mazo son del side deck."""

    deck = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="side_cards")
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name="+")
    quantity = models.PositiveSmallIntegerField(default=1)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["deck", "card"], name="unique_side_card")]


class DeckVersion(models.Model):
    deck = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="deck_versions")
    number = models.PositiveIntegerField()  # v1, v2… dentro del mazo
    name = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    # Guardada a mano o sola al anotar una partida con el mazo cambiado.
    automatic = models.BooleanField(default=False)
    # La lista principal del mazo (como mucho una por mazo).
    principal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["deck", "-number"]
        constraints = [
            models.UniqueConstraint(fields=["deck", "number"], name="unique_deck_version_number"),
            models.UniqueConstraint(
                fields=["deck"], condition=models.Q(principal=True), name="single_principal_version"
            ),
        ]

    def __str__(self):
        return f"{self.deck} v{self.number}"


class DeckVersionCard(models.Model):
    class Section(models.TextChoices):
        MAIN = "main", "Main deck"
        Z = "z", "Z Deck"
        SIDE = "side", "Side deck"

    version = models.ForeignKey(DeckVersion, on_delete=models.CASCADE, related_name="cards")
    card = models.ForeignKey(Card, on_delete=models.PROTECT, related_name="+")
    section = models.CharField(max_length=4, choices=Section.choices)
    quantity = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["version", "card", "section"], name="unique_version_card_section")
        ]


class Match(models.Model):
    class Result(models.TextChoices):
        WIN = "win", "Win"
        LOSS = "loss", "Loss"
        DRAW = "draw", "Draw"

    version = models.ForeignKey(DeckVersion, on_delete=models.CASCADE, related_name="matches")
    played_on = models.DateField()
    # Líder rival: una carta Líder del catálogo (por id de Bandai, como el resto de proyectos).
    opponent_leader_bandai_id = models.PositiveIntegerField(null=True, blank=True)
    opponent_leader_name = models.CharField(max_length=200, blank=True)
    opponent_name = models.CharField(max_length=120, blank=True)
    result = models.CharField(max_length=4, choices=Result.choices)
    went_first = models.BooleanField(null=True, blank=True)  # None = no lo sé
    score = models.CharField(max_length=10, blank=True)  # p. ej. "2-1"
    event = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-played_on", "-created_at"]
