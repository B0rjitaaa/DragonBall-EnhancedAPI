from django.db.models import Count, Q, Sum
from rest_framework import serializers

from .models import Location


class LocationSerializer(serializers.ModelSerializer):
    cards = serializers.IntegerField(read_only=True, default=0)
    copies = serializers.IntegerField(read_only=True, default=0)
    fakes = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Location
        fields = ["id", "uid", "name", "kind", "notes", "is_default", "position", "cards", "copies", "fakes"]
        read_only_fields = ["uid", "is_default"]

    @staticmethod
    def annotate(queryset):
        return queryset.annotate(
            cards=Count("entries__card", distinct=True),
            copies=Sum("entries__quantity", default=0),
            fakes=Sum("entries__quantity", filter=Q(entries__fake=True), default=0),
        )

    @classmethod
    def listing(cls) -> list[dict]:
        """Todas las ubicaciones con sus totales ("Sin ubicar" siempre existe)."""
        Location.default()
        # Meta.ordering no se aplica a consultas agregadas: hay que repetirlo.
        return cls(cls.annotate(Location.objects.all()).order_by(*Location._meta.ordering), many=True).data
