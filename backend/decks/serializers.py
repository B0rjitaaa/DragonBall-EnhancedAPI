from rest_framework import serializers

from .models import DeckVersion, Match


class MatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Match
        fields = [
            "id", "version", "played_on", "opponent_leader_bandai_id", "opponent_leader_name", "opponent_name",
            "result", "went_first", "score", "event", "notes", "created_at",
        ]
        read_only_fields = ["created_at"]
        extra_kwargs = {"version": {"required": False}}


class VersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeckVersion
        fields = ["id", "number", "name", "notes", "automatic", "principal", "created_at"]
        read_only_fields = ["number", "automatic", "principal", "created_at"]


class SideSerializer(serializers.Serializer):
    bandai_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=0, max_value=99)


class ListCardSerializer(serializers.Serializer):
    bandai_id = serializers.IntegerField()
    section = serializers.ChoiceField(choices=["main", "z", "side"])
    quantity = serializers.IntegerField(min_value=0, max_value=99)
