from django.db.models import Exists, OuterRef
from django.urls import reverse
from django.utils import timezone

from apps.access.services import get_demo_profile, get_demo_user_reference
from apps.configuration.models import (
    BookingPolicy,
    CalendarException,
    OperatingSchedule,
    ReportConfiguration,
    RoomNotice,
    Shift,
    Weekday,
)
from apps.configuration.selectors import (
    get_active_room_notices,
    get_booking_policy_for_date,
)
from apps.core.enums import DemoProfile
from apps.operations.models import UseSession

from .common import (
    SCREEN_META,
    SUPERVISOR_NAV_ITEMS,
    _render_screen,
)


def _screen_context(request, *, screen, query="", search_url_name=None):
    profile = get_demo_profile(request)
    title, section_title, search_placeholder = SCREEN_META[screen]
    return {
        "area": "supervisor",
        "screen": screen,
        "screen_title": title,
        "section_title": section_title,
        "search_placeholder": search_placeholder,
        "search_url": reverse(search_url_name) if search_url_name else "",
        "query": query,
        "nav_items": [
            {**item, "url": reverse(item["url_name"])} for item in SUPERVISOR_NAV_ITEMS
        ],
        "current_profile_label": DemoProfile(profile).label,
        "current_user_reference": get_demo_user_reference(request),
        "active_notices": get_active_room_notices(),
        "area_switch_url": reverse("web:monitor-dashboard"),
        "area_switch_label": "Painel operacional",
    }


def _window_string(day):
    if day is None or not day.is_open:
        return ""
    return ",".join(
        f"{window.opens_at:%H:%M}-{window.closes_at:%H:%M}"
        for window in day.windows.all()
    )


def _weekday_fields(*, post_data=None, schedule=None):
    existing = {day.weekday: day for day in schedule.days.all()} if schedule else {}
    return [
        {
            "weekday": value,
            "label": label,
            "name": f"windows_{value}",
            "value": (
                post_data.get(f"windows_{value}", "")
                if post_data is not None
                else _window_string(existing.get(value))
            ),
        }
        for value, label in Weekday.choices
    ]


def _parse_schedule_days(post_data):
    days = []
    for weekday in Weekday.values:
        raw_value = post_data.get(f"windows_{weekday}", "").strip()
        windows = []
        if raw_value:
            for display_order, raw_window in enumerate(raw_value.split(",")):
                pieces = [piece.strip() for piece in raw_window.split("-")]
                if len(pieces) != 2 or not all(pieces):
                    raise ValueError(
                        "Use o formato HH:MM-HH:MM, separando janelas por vírgula."
                    )
                windows.append(
                    {
                        "opens_at": pieces[0],
                        "closes_at": pieces[1],
                        "display_order": display_order,
                    }
                )
        days.append(
            {
                "weekday": weekday,
                "is_open": bool(windows),
                "windows": windows,
            }
        )
    return days


def _decorate_schedules(schedules, *, post_data=None, active_schedule_id=None):
    values = list(schedules)
    today = timezone.localdate()
    for schedule in values:
        schedule.type_label = schedule.get_schedule_type_display()
        schedule.can_replace = schedule.is_active and (
            schedule.valid_until is None
            or schedule.valid_until > max(today, schedule.valid_from)
        )
        schedule.weekday_fields = _weekday_fields(
            post_data=(
                post_data
                if active_schedule_id is not None and schedule.pk == active_schedule_id
                else None
            ),
            schedule=schedule,
        )
    return values


def _report_configuration():
    return ReportConfiguration.objects.filter(is_active=True).first()


def _configuration_context(
    request,
    *,
    section=None,
    form_error="",
    form_data=None,
    form_kind="",
    preview_result=None,
    preview_schedule_id=None,
):
    section = section or request.GET.get("section", "schedules")
    allowed_sections = {"schedules", "shifts", "exceptions", "notices", "policies"}
    if section not in allowed_sections:
        section = "schedules"
    active_schedule_id = int(preview_schedule_id) if preview_schedule_id else None
    schedules = _decorate_schedules(
        OperatingSchedule.objects.prefetch_related("days__windows"),
        post_data=form_data,
        active_schedule_id=active_schedule_id,
    )
    today = timezone.localdate()
    current_policy = get_booking_policy_for_date(today)
    latest_policy = BookingPolicy.objects.order_by(
        "valid_from", "created_at", "pk"
    ).last()
    future_policy = (
        BookingPolicy.objects.filter(valid_from__gt=today)
        .order_by("valid_from", "created_at", "pk")
        .first()
    )
    context = _screen_context(request, screen="calendar")
    context.update(
        {
            "configuration_section": section,
            "schedules": schedules,
            "schedule_types": OperatingSchedule.ScheduleType.choices,
            "new_weekday_fields": _weekday_fields(
                post_data=form_data if form_kind == "schedule-create" else None
            ),
            "shifts": Shift.objects.annotate(
                has_sessions=Exists(
                    UseSession.objects.filter(start_shift_id=OuterRef("pk"))
                )
            ),
            "exceptions": CalendarException.objects.all(),
            "exception_types": CalendarException.ExceptionType.choices,
            "notices": RoomNotice.objects.all(),
            "notice_types": RoomNotice.NoticeType.choices,
            "current_booking_policy": current_policy,
            "future_booking_policy": future_policy,
            "latest_booking_policy": latest_policy,
            "booking_policy": latest_policy or current_policy,
            "report_configuration": _report_configuration(),
            "report_formats": ReportConfiguration.ExportFormat.choices,
            "form_error": form_error,
            "form_data": form_data or {},
            "form_kind": form_kind,
            "form_shift_id": (
                int(form_kind.removeprefix("shift-edit-"))
                if form_kind.startswith("shift-edit-")
                else None
            ),
            "preview_result": preview_result,
            "preview_schedule_id": active_schedule_id,
        }
    )
    return context


def _configuration_error(
    request,
    *,
    section,
    error,
    status,
    form_kind,
    form_data=None,
    preview_result=None,
    preview_schedule_id=None,
):
    return _render_screen(
        request,
        content_template="supervisor/partials/configuration.html",
        context=_configuration_context(
            request,
            section=section,
            form_error=error,
            form_data=form_data or request.POST,
            form_kind=form_kind,
            preview_result=preview_result,
            preview_schedule_id=preview_schedule_id,
        ),
        status=status,
    )


__all__ = [
    "_configuration_context",
    "_configuration_error",
    "_parse_schedule_days",
    "_report_configuration",
    "_screen_context",
]

