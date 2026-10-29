from itertools import groupby

from django.contrib import admin, messages
from django.http import FileResponse, Http404, HttpResponseNotAllowed
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path

from . import services
from .models import Backup


@admin.register(Backup)
class BackupAdmin(admin.ModelAdmin):
    """Página propia (no hay tabla): estado, «Hacer copia ahora», la lista de copias y descargas."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        view = self.admin_site.admin_view
        return [
            path("request/", view(self.request_view), name="backups_backup_request"),
            path("download/<path:relative>", view(self.download_view), name="backups_backup_download"),
        ] + super().get_urls()

    def changelist_view(self, request, extra_context=None):
        state = services.status()
        copies = services.list_copies()
        context = {
            **self.admin_site.each_context(request),
            "title": "Backups",
            "opts": self.model._meta,
            "state": state,
            "groups": [(name, list(items)) for name, items in groupby(copies, key=lambda c: c.group)],
            # Mientras hay una en curso o pedida, la página se recarga sola.
            "refresh": state.get("running") or state.get("requested"),
        }
        return TemplateResponse(request, "admin/backups/backup_list.html", context)

    def request_view(self, request):
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        try:
            services.request_backup()
        except (RuntimeError, OSError) as exc:
            self.message_user(request, f"Could not request the backup: {exc}", messages.ERROR)
        else:
            self.message_user(request, "Backup requested: it will start in a few seconds and takes about 15 minutes.")
        return redirect("admin:backups_backup_changelist")

    def download_view(self, request, relative):
        try:
            path = services.download_path(relative)
        except FileNotFoundError:
            raise Http404("That backup does not exist")
        return FileResponse(path.open("rb"), as_attachment=True, filename=f"{path.parent.name}_{path.name}")
