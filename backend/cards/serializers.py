from rest_framework import serializers

from .models import BanListEntry, Card, CardChange, CardErrata, CardRuling, KeywordSkill, SyncRun
from prices.services import card_price

from .thumbs import thumb_url


def print_ref(card_number: str, index: int) -> str:
    """Enlace legible de una impresión: el número para la primera (por orden de alta) y -2, -3… para las
    demás. Las impresiones nuevas van al final: los enlaces ya compartidos no cambian."""
    return card_number if index == 0 else f"{card_number}-{index + 1}"


def card_ref(card: Card) -> str:
    position = Card.objects.filter(card_number=card.card_number, id__lt=card.id).count()
    return print_ref(card.card_number, position)


def card_from_ref(ref: str) -> Card | None:
    """La carta de un enlace: un id de Bandai, un número (su primera impresión) o número-N (la N-ésima)."""
    if ref.isdigit():
        return Card.objects.filter(id=int(ref)).first()
    prints = list(Card.objects.filter(card_number__iexact=ref).order_by("id")[:1])
    if prints:
        return prints[0]
    number, _, index = ref.rpartition("-")
    if number and index.isdigit() and int(index) >= 2:
        prints = list(Card.objects.filter(card_number__iexact=number).order_by("id"))
        if int(index) <= len(prints):
            return prints[int(index) - 1]
    return None


class CardListSerializer(serializers.ModelSerializer):
    has_back = serializers.BooleanField(read_only=True)
    # Miniatura para cuadrículas y listas (ver cards/thumbs.py); la imagen completa sigue en image_url.
    thumb_url = serializers.SerializerMethodField()
    # Precio de Cardmarket en € (ver prices/); mejor con select_related("cardmarket__product").
    price = serializers.SerializerMethodField()

    class Meta:
        model = Card
        fields = [
            "id", "card_number", "name", "image_url", "thumb_url", "card_type", "colors", "rarity", "rarity_code",
            "energy", "power", "set_code", "card_set", "has_back", "back_name", "back_image_url",
            "legality", "legality_since", "keyword_skills", "has_errata", "rulings_count", "price",
        ]

    def get_thumb_url(self, card) -> str:
        return thumb_url(card.id, card.image_url)

    def get_price(self, card) -> dict | None:
        return card_price(card)


class CardChangeSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    thumb_url = serializers.SerializerMethodField()

    class Meta:
        model = CardChange
        fields = ["id", "kind", "kind_label", "created_at", "card_id", "card_number", "card_name",
                  "thumb_url", "field", "before", "after"]

    def get_thumb_url(self, change) -> str:
        card = change.card
        return thumb_url(card.id, card.image_url) if card and card.image_url else ""


class CardErrataSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardErrata
        fields = ["card_name", "before", "after", "notes", "image_url", "date", "list_updated"]


class CardRulingSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardRuling
        fields = ["order", "question", "answer", "is_new", "set_label"]


class CardDetailSerializer(serializers.ModelSerializer):
    has_back = serializers.BooleanField(read_only=True)
    errata = serializers.SerializerMethodField()
    rulings = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    # Historial de su precio (solo los cambios), para la gráfica del detalle.
    price_history = serializers.SerializerMethodField(method_name="get_history")
    # Enlace legible (?card=BT20-149, ?card=BT20-149-2…) y las demás impresiones de su número.
    ref = serializers.SerializerMethodField()
    prints = serializers.SerializerMethodField()

    class Meta:
        model = Card
        exclude = ["raw", "effect_text", "search_text"]

    def get_errata(self, card) -> dict | None:
        if not card.has_errata:
            return None
        entry = CardErrata.objects.filter(card_number=card.card_number).first()
        return CardErrataSerializer(entry).data if entry else None

    def get_price(self, card) -> dict | None:
        return card_price(card, changes=True)

    def get_history(self, card) -> list:
        from prices.models import PricePoint

        return [{"date": d.isoformat(), "eur": float(e)}
                for d, e in PricePoint.objects.filter(card=card).order_by("date").values_list("date", "eur")]

    def get_ref(self, card) -> str:
        return card_ref(card)

    def get_prints(self, card) -> list:
        prints = Card.objects.filter(card_number=card.card_number).order_by("id") \
            .values("id", "rarity_code", "card_set", "image_url")
        return [{**p, "ref": print_ref(card.card_number, i), "thumb_url": thumb_url(p["id"], p["image_url"])}
                for i, p in enumerate(prints)] if len(prints) > 1 else []

    def get_rulings(self, card) -> list:
        if not card.rulings_count:
            return []
        qs = CardRuling.objects.filter(card_number=card.card_number).order_by("order")
        return CardRulingSerializer(qs, many=True).data


class SyncRunSerializer(serializers.ModelSerializer):
    failed = serializers.SerializerMethodField()

    class Meta:
        model = SyncRun
        exclude = ["failed_ids"]

    def get_failed(self, obj) -> int:
        return len(obj.failed_ids)


class SearchRequestSerializer(serializers.Serializer):
    q = serializers.CharField(required=False, allow_blank=True, max_length=200,
                              help_text="Free-text search in name, number and text")
    query = serializers.JSONField(required=False, allow_null=True, help_text="AND/OR tree of conditions")
    ordering = serializers.CharField(required=False, allow_blank=True)
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=200, default=48)
    scope = serializers.ChoiceField(choices=["all", "collection"], required=False, default="all",
                                    help_text="collection: only the cards in My collection (with their copies)")
    location = serializers.IntegerField(required=False, allow_null=True,
                                        help_text="With scope=collection: only the copies in that location")
    fake = serializers.BooleanField(required=False, allow_null=True, default=None,
                                    help_text="With scope=collection and true: only cards with fake copies")
    include_fakes = serializers.BooleanField(required=False, allow_null=True, default=None,
                                             help_text="With scope=collection: also count fake copies "
                                                       "(by default only genuine ones)")


class BanListEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = BanListEntry
        fields = ["card_number", "status", "card_name", "limit", "since"]


class KeywordSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = KeywordSkill
        fields = ["name", "category", "description", "order"]
