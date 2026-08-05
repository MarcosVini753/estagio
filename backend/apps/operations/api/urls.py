from django.urls import path

from .views import (
    ActiveUsageSessionListAPIView,
    CurrentUsageSessionAPIView,
    MyReservationListAPIView,
    ReservationCancelAPIView,
    ReservationListCreateAPIView,
    UsageSessionCorrectionAPIView,
    UsageSessionFinishAPIView,
    UsageSessionHistoryAPIView,
    UsageSessionStartAPIView,
    UsageSessionSwitchAPIView,
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
    path(
        "usage-sessions/current/",
        CurrentUsageSessionAPIView.as_view(),
        name="usage-session-current",
    ),
    path(
        "usage-sessions/active/",
        ActiveUsageSessionListAPIView.as_view(),
        name="usage-session-active",
    ),
    path(
        "usage-sessions/history/",
        UsageSessionHistoryAPIView.as_view(),
        name="usage-session-history",
    ),
    path(
        "usage-sessions/start/",
        UsageSessionStartAPIView.as_view(),
        name="usage-session-start",
    ),
    path(
        "usage-sessions/<int:pk>/switch-computer/",
        UsageSessionSwitchAPIView.as_view(),
        name="usage-session-switch",
    ),
    path(
        "usage-sessions/<int:pk>/finish/",
        UsageSessionFinishAPIView.as_view(),
        name="usage-session-finish",
    ),
    path(
        "usage-sessions/<int:pk>/correct/",
        UsageSessionCorrectionAPIView.as_view(),
        name="usage-session-correct",
    ),
]
