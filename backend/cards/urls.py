from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("cards", views.CardViewSet, basename="card")
router.register("sync", views.SyncRunViewSet, basename="sync")

urlpatterns = [
    path("fields/", views.FieldsView.as_view(), name="fields"),
    path("facets/", views.FacetsView.as_view(), name="facets"),
    path("banlist/", views.BanListView.as_view(), name="banlist"),
    *router.urls,
]
