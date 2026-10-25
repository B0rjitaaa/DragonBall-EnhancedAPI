from django.contrib import admin

from .models import DeckVersion, Match


class MatchInline(admin.TabularInline):
    model = Match
    extra = 0


@admin.register(DeckVersion)
class DeckVersionAdmin(admin.ModelAdmin):
    list_display = ["deck", "number", "name", "automatic", "created_at"]
    list_filter = ["deck"]
    inlines = [MatchInline]
