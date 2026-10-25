from django.urls import path

from . import views

# Bajo /api/my-collection/ (ver config/urls.py).
urlpatterns = [
    path("decks/<int:pk>/", views.DeckView.as_view(), name="deck"),
    path("decks/<int:pk>/versions/", views.DeckVersionsView.as_view(), name="deck-versions"),
    path("decks/<int:pk>/matches/", views.DeckMatchesView.as_view(), name="deck-matches"),
    path("decks/<int:pk>/plan/", views.DeckPlanView.as_view(), name="deck-plan"),
    path("decks/<int:pk>/side/", views.DeckSideView.as_view(), name="deck-side"),
    path("deck-versions/<int:pk>/", views.VersionDetailView.as_view(), name="deck-version"),
    path("deck-versions/<int:pk>/restore/", views.VersionRestoreView.as_view(), name="deck-version-restore"),
    path("matches/<int:pk>/", views.MatchDetailView.as_view(), name="match"),
]
