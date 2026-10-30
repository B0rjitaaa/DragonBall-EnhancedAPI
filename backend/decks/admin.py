from django.contrib import admin

from .models import DeckVersion, Match, PickList


class MatchInline(admin.TabularInline):
    model = Match
    extra = 0


@admin.register(DeckVersion)
class DeckVersionAdmin(admin.ModelAdmin):
    list_display = ["deck", "number", "name", "automatic", "created_at"]
    list_filter = ["deck"]
    inlines = [MatchInline]


@admin.register(PickList)
class PickListAdmin(admin.ModelAdmin):
    list_display = ("deck", "created_at", "picked")
    readonly_fields = ("deck", "groups", "created_at")

    @admin.display(description="Picked")
    def picked(self, obj):
        return f"{len(obj.done)}/{obj.total}"
