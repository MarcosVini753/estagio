from django.urls import path

from .views import (
    BookingPolicyAPIView,
    CalendarExceptionDetailAPIView,
    CalendarExceptionListCreateAPIView,
    ShiftDetailAPIView,
    ShiftListCreateAPIView,
)

urlpatterns = [
    path("shifts/", ShiftListCreateAPIView.as_view(), name="shift-list"),
    path("shifts/<int:pk>/", ShiftDetailAPIView.as_view(), name="shift-detail"),
    path(
        "calendar-exceptions/",
        CalendarExceptionListCreateAPIView.as_view(),
        name="calendar-exception-list",
    ),
    path(
        "calendar-exceptions/<int:pk>/",
        CalendarExceptionDetailAPIView.as_view(),
        name="calendar-exception-detail",
    ),
    path(
        "booking-policy/",
        BookingPolicyAPIView.as_view(),
        name="booking-policy",
    ),
]
