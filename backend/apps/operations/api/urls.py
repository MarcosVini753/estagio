from django.urls import path

from .views import (
    MyReservationListAPIView,
    ReservationCancelAPIView,
    ReservationListCreateAPIView,
)

urlpatterns = [
    path(
        "reservations/", ReservationListCreateAPIView.as_view(), name="reservation-list"
    ),
    path(
        "reservations/mine/",
        MyReservationListAPIView.as_view(),
        name="reservation-mine",
    ),
    path(
        "reservations/<int:pk>/cancel/",
        ReservationCancelAPIView.as_view(),
        name="reservation-cancel",
    ),
]
