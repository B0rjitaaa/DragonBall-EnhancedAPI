from django.urls import path

from . import views

# Bajo /api/my-collection/ (ver config/urls.py).
urlpatterns = [
    path("decks/import/preview/", views.DeckImportPreviewView.as_view(), name="deck-import-preview"),
    path("decks/import/", views.DeckImportView.as_view(), name="deck-import"),
    path("decks/<int:pk>/", views.DeckView.as_view(), name="deck"),
    path("decks/<int:pk>/versions/", views.DeckVersionsView.as_view(), name="deck-versions"),
    path("decks/<int:pk>/matches/", views.DeckMatchesView.as_view(), name="deck-matches"),
    path("decks/<int:pk>/plan/", views.DeckPlanView.as_view(), name="deck-plan"),
    path("decks/<int:pk>/side/", views.DeckSideView.as_view(), name="deck-side"),
    path("decks/<int:pk>/pick-list/", views.DeckPickListView.as_view(), name="deck-pick-list"),
    path("decks/<int:pk>/to-history/", views.DeckToHistoryView.as_view(), name="deck-to-history"),
    path("decks/<int:pk>/back-in-use/", views.DeckBackInUseView.as_view(), name="deck-back-in-use"),
    path("deck-versions/<int:pk>/", views.VersionDetailView.as_view(), name="deck-version"),
    path("deck-versions/<int:pk>/restore/", views.VersionRestoreView.as_view(), name="deck-version-restore"),
    path("matches/<int:pk>/", views.MatchDetailView.as_view(), name="match"),
]
