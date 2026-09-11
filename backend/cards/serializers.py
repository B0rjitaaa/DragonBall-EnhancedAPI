from rest_framework import serializers

from .models import BanListEntry, Card, KeywordSkill, SyncRun


class CardListSerializer(serializers.ModelSerializer):
    has_back = serializers.BooleanField(read_only=True)

    class Meta:
        model = Card
        fields = [
            "id", "card_number", "name", "image_url", "card_type", "colors", "rarity", "rarity_code",
            "energy", "power", "set_code", "card_set", "has_back", "back_name", "back_image_url",
            "legality", "legality_since", "keyword_skills",
        ]


class CardDetailSerializer(serializers.ModelSerializer):
    has_back = serializers.BooleanField(read_only=True)

    class Meta:
        model = Card
        exclude = ["raw", "effect_text", "search_text"]


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


class BanListEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = BanListEntry
        fields = ["card_number", "status", "card_name", "limit", "since"]


class KeywordSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = KeywordSkill
        fields = ["name", "category", "description", "order"]
