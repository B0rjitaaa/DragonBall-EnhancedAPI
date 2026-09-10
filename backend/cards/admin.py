from django.contrib import admin

from .models import BanListEntry, Card, SyncRun


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ("card_number", "name", "card_type", "rarity_code", "energy", "power", "set_code", "legality")
    list_filter = ("legality", "card_type", "series", "rarity_code")
    search_fields = ("card_number", "name", "text")
    readonly_fields = ("raw", "created_at", "updated_at")


@admin.register(SyncRun)
class SyncRunAdmin(admin.ModelAdmin):
    list_display = ("started_at", "finished_at", "status", "full", "listed", "created", "updated")
    list_filter = ("status", "full")
    readonly_fields = [f.name for f in SyncRun._meta.fields]


@admin.register(BanListEntry)
class BanListEntryAdmin(admin.ModelAdmin):
    list_display = ("card_number", "card_name", "status", "limit", "since", "source", "list_updated")
    list_filter = ("status", "source")
    search_fields = ("card_number", "card_name")
