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
    path("keyword-skills/", views.KeywordSkillsView.as_view(), name="keyword-skills"),
    path("my-collection/", views.MyCollectionView.as_view(), name="my-collection"),
    path("my-collection/adjust/", views.MyCollectionAdjustView.as_view(), name="my-collection-adjust"),
    path("my-collection/backup/", views.MyCollectionBackupView.as_view(), name="my-collection-backup"),
    path("my-collection/move/", views.MyCollectionMoveView.as_view(), name="my-collection-move"),
    path("my-collection/note/", views.MyCollectionNoteView.as_view(), name="my-collection-note"),
    path("my-collection/reorder/", views.MyCollectionReorderView.as_view(), name="my-collection-reorder"),
    path("my-collection/locations/", views.LocationsView.as_view(), name="my-collection-locations"),
    path("my-collection/locations/<int:pk>/", views.LocationDetailView.as_view(), name="my-collection-location"),
    *router.urls,
]
