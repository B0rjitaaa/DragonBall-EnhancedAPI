from django.contrib import admin

from .models import Activity, RestorePoint


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("updated_at", "title", "kind", "source", "undone_at")
    list_filter = ("kind", "source")
    search_fields = ("title",)
    readonly_fields = [f.name for f in Activity._meta.fields]


@admin.register(RestorePoint)
class RestorePointAdmin(admin.ModelAdmin):
    list_display = ("created_at", "reason")
    exclude = ("snapshot",)
    readonly_fields = ("created_at", "reason", "activity")
