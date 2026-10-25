from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("scans", views.ScanViewSet, basename="scan")
router.register("sessions", views.ScanSessionViewSet, basename="session")

# Bajo /api/scanner/ (ver config/urls.py).
urlpatterns = [
    path("camera/preview/", views.camera_preview, name="camera-preview"),
    path("", include(router.urls)),
]
