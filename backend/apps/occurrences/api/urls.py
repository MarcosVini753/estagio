from django.urls import path

from .views import OccurrenceDetailAPIView, OccurrenceListCreateAPIView

urlpatterns = [
    path("occurrences/", OccurrenceListCreateAPIView.as_view(), name="occurrence-list"),
    path(
        "occurrences/<int:pk>/",
        OccurrenceDetailAPIView.as_view(),
        name="occurrence-detail",
    ),
]
