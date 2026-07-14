from django.urls import path

from .views import (
    ComputerAvailabilityAPIView,
    ComputerDetailAPIView,
    ComputerListCreateAPIView,
    ComputerOperationalStateAPIView,
    ComputerSlotsAPIView,
)

urlpatterns = [
    path("availability/", ComputerAvailabilityAPIView.as_view(), name="availability"),
    path("<int:pk>/slots/", ComputerSlotsAPIView.as_view(), name="computer-slots"),
    path(
        "<int:pk>/operational-state/",
        ComputerOperationalStateAPIView.as_view(),
        name="computer-operational-state",
    ),
    path("<int:pk>/", ComputerDetailAPIView.as_view(), name="computer-detail"),
    path("", ComputerListCreateAPIView.as_view(), name="computer-list"),
]
