from django.urls import path

from .views import (
    ActiveRoomNoticeListAPIView,
    BookingPolicyAPIView,
    CalendarExceptionDetailAPIView,
    CalendarExceptionListCreateAPIView,
    OperatingScheduleDetailAPIView,
    OperatingScheduleImpactPreviewAPIView,
    OperatingScheduleListCreateAPIView,
    OperatingScheduleReplaceAPIView,
    RoomNoticeDetailAPIView,
    RoomNoticeListCreateAPIView,
    RoomStatusAPIView,
    ShiftDetailAPIView,
    ShiftListCreateAPIView,
    ShiftReplaceAPIView,
)

urlpatterns = [
    path("room-status/", RoomStatusAPIView.as_view(), name="room-status"),
    path(
        "operating-schedules/impact-preview/",
        OperatingScheduleImpactPreviewAPIView.as_view(),
        name="operating-schedule-impact-preview",
    ),
    path(
        "operating-schedules/",
        OperatingScheduleListCreateAPIView.as_view(),
        name="operating-schedule-list",
    ),
    path(
        "operating-schedules/<int:pk>/replace/",
        OperatingScheduleReplaceAPIView.as_view(),
        name="operating-schedule-replace",
    ),
    path(
        "operating-schedules/<int:pk>/",
        OperatingScheduleDetailAPIView.as_view(),
        name="operating-schedule-detail",
    ),
    path(
        "room-notices/active/",
        ActiveRoomNoticeListAPIView.as_view(),
        name="room-notice-active",
    ),
    path(
        "room-notices/",
        RoomNoticeListCreateAPIView.as_view(),
        name="room-notice-list",
    ),
    path(
        "room-notices/<int:pk>/",
        RoomNoticeDetailAPIView.as_view(),
        name="room-notice-detail",
    ),
    path("shifts/", ShiftListCreateAPIView.as_view(), name="shift-list"),
    path("shifts/<int:pk>/", ShiftDetailAPIView.as_view(), name="shift-detail"),
    path(
        "shifts/<int:pk>/replace/",
        ShiftReplaceAPIView.as_view(),
        name="shift-replace",
    ),
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
