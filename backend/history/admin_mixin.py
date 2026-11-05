"""Lo que se cambie desde el admin de Django (copias, ubicaciones, listas) también queda en el histórico."""
from .recorder import record


class RecordedAdmin:
    def _recorded(self, request, view, *args, **kwargs):
        if request.method != "POST":
            return view(request, *args, **kwargs)
        with record("admin", source="admin"):
            return view(request, *args, **kwargs)

    def changeform_view(self, request, *args, **kwargs):
        return self._recorded(request, super().changeform_view, *args, **kwargs)

    def delete_view(self, request, *args, **kwargs):
        return self._recorded(request, super().delete_view, *args, **kwargs)

    def changelist_view(self, request, *args, **kwargs):
        # Acciones en bloque («Delete selected…») y la edición en la lista.
        return self._recorded(request, super().changelist_view, *args, **kwargs)
