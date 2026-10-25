from django.contrib import admin

from .models import CollectionEntry, Location


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ["name", "kind", "is_default", "position"]
    list_filter = ["kind"]


@admin.register(CollectionEntry)
class CollectionEntryAdmin(admin.ModelAdmin):
    list_display = ["card", "location", "quantity", "fake"]
    list_filter = ["location", "fake"]
    search_fields = ["card__name", "card__card_number", "notes"]
    raw_id_fields = ["card"]
