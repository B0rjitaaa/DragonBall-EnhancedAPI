from rest_framework import serializers

from .models import BanListEntry, Card, CardErrata, CardRuling, KeywordSkill, SyncRun
from .thumbs import thumb_url


class CardListSerializer(serializers.ModelSerializer):
    has_back = serializers.BooleanField(read_only=True)
    # Miniatura para cuadrículas y listas (ver cards/thumbs.py); la imagen completa sigue en image_url.
    thumb_url = serializers.SerializerMethodField()

    class Meta:
        model = Card
        fields = [
            "id", "card_number", "name", "image_url", "thumb_url", "card_type", "colors", "rarity", "rarity_code",
            "energy", "power", "set_code", "card_set", "has_back", "back_name", "back_image_url",
            "legality", "legality_since", "keyword_skills", "has_errata", "rulings_count",
        ]

    def get_thumb_url(self, card) -> str:
        return thumb_url(card.id, card.image_url)


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

    class Meta:
        model = Card
        exclude = ["raw", "effect_text", "search_text"]

    def get_errata(self, card) -> dict | None:
        if not card.has_errata:
            return None
        entry = CardErrata.objects.filter(card_number=card.card_number).first()
        return CardErrataSerializer(entry).data if entry else None

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
                              help_text="Búsqueda libre en nombre, número y texto")
    query = serializers.JSONField(required=False, allow_null=True, help_text="Árbol AND/OR de condiciones")
    ordering = serializers.CharField(required=False, allow_blank=True)
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=200, default=48)
    scope = serializers.ChoiceField(choices=["all", "collection"], required=False, default="all",
                                    help_text="collection: solo las cartas de Mi colección (con sus copias)")
    location = serializers.IntegerField(required=False, allow_null=True,
                                        help_text="Con scope=collection: solo las copias de esa ubicación")
    fake = serializers.BooleanField(required=False, allow_null=True, default=None,
                                    help_text="Con scope=collection y true: solo las cartas con copias falsas")
    include_fakes = serializers.BooleanField(required=False, allow_null=True, default=None,
                                             help_text="Con scope=collection: contar también las copias falsas "
                                                       "(por defecto solo las auténticas)")


class BanListEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = BanListEntry
        fields = ["card_number", "status", "card_name", "limit", "since"]


class KeywordSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = KeywordSkill
        fields = ["name", "category", "description", "order"]
