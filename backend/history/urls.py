from django.urls import path

from . import views

# Bajo /api/history/ (ver config/urls.py).
urlpatterns = [
    path("", views.HistoryView.as_view(), name="history"),
    path("csv/", views.HistoryCsvView.as_view(), name="history-csv"),
    path("restore-points/", views.RestorePointsView.as_view(), name="history-restore-points"),
    path("restore-points/<int:pk>/", views.RestorePointRestoreView.as_view(), name="history-restore-point"),
    path("<int:pk>/", views.HistoryDetailView.as_view(), name="history-detail"),
    path("<int:pk>/undo/", views.HistoryUndoView.as_view(), name="history-undo"),
]
