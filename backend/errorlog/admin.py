from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import ErrorGroup


class StatusFilter(admin.SimpleListFilter):
    """Por defecto, solo los pendientes."""

    title = "status"
    parameter_name = "estado"

    def lookups(self, request, model_admin):
        return [("pendientes", "Pending"), ("resueltos", "Resolved"), ("todos", "All")]

    def choices(self, changelist):
        current = self.value() or "pendientes"
        for value, label in self.lookup_choices:
            yield {
                "selected": current == value,
                "query_string": changelist.get_query_string({self.parameter_name: value}),
                "display": label,
            }

    def queryset(self, request, queryset):
        value = self.value() or "pendientes"
        if value == "pendientes":
            return queryset.filter(resolved_at__isnull=True)
        if value == "resueltos":
            return queryset.filter(resolved_at__isnull=False)
        return queryset


@admin.register(ErrorGroup)
class ErrorGroupAdmin(admin.ModelAdmin):
    list_display = ["pending", "source", "kind", "short_message", "count", "last_seen", "first_seen"]
    list_display_links = ["kind", "short_message"]
    list_filter = [StatusFilter, "source", "last_seen"]
    search_fields = ["kind", "message", "where", "request"]
    date_hierarchy = "last_seen"
    actions = ["mark_resolved", "reopen"]
    fields = ["source", "kind", "message", "where", "request", "user_agent", "count", "first_seen", "last_seen",
              "resolved_at", "trace"]
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="pending", boolean=True, ordering="resolved_at")
    def pending(self, obj):
        return obj.resolved_at is None

    @admin.display(description="message")
    def short_message(self, obj):
        first = obj.message.splitlines()[0] if obj.message else ""
        return first[:120] + ("…" if len(first) > 120 else "")

    @admin.display(description="traceback")
    def trace(self, obj):
        if not obj.traceback:
            return "—"
        return format_html('<pre style="white-space: pre-wrap; max-width: 100%; font-size: 12px">{}</pre>', obj.traceback)

    @admin.action(description="Mark as resolved")
    def mark_resolved(self, request, queryset):
        n = queryset.filter(resolved_at__isnull=True).update(resolved_at=timezone.now())
        self.message_user(request, f"{n} errors marked as resolved. If they happen again, they reopen by themselves.")

    @admin.action(description="Reopen")
    def reopen(self, request, queryset):
        n = queryset.exclude(resolved_at__isnull=True).update(resolved_at=None)
        self.message_user(request, f"{n} errors reopened.")
