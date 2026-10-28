from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from errorlog.views import WebErrorView
from prices.views import RadarView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("cards.urls")),
    path("api/my-collection/", include("decks.urls")),
    path("api/scanner/", include("scanner.urls")),
    path("api/errors/", WebErrorView.as_view(), name="web-errors"),
    path("api/prices/radar/", RadarView.as_view(), name="prices-radar"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]

# Páginas de error propias (JSON en la API, página en español en lo demás). Solo con DEBUG desactivado.
handler400 = "config.errors.bad_request"
handler403 = "config.errors.permission_denied"
handler404 = "config.errors.page_not_found"
handler500 = "config.errors.server_error"

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
