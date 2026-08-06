from datetime import date, datetime

from django.db.models import Q
from django.utils import timezone

from .models import (
    BookingPolicy,
    CalendarException,
    OperatingSchedule,
    OperatingScheduleDay,
    RoomNotice,
    Shift,
)


def get_shifts_for_date(target_date: date):
    return (
        Shift.objects.filter(is_active=True, valid_from__lte=target_date)
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=target_date))
        .order_by("display_order", "start_time")
    )


def get_calendar_exception_for_date(target_date: date):
    return CalendarException.objects.filter(date=target_date).first()


def _schedule_for_date(target_date: date, schedule_type: str):
    return (
        OperatingSchedule.objects.filter(
            schedule_type=schedule_type,
            is_active=True,
            valid_from__lte=target_date,
        )
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=target_date))
        .prefetch_related("days__windows")
        .order_by("-valid_from", "-created_at")
        .first()
    )


def get_regular_operating_schedule_for_date(target_date: date):
    return _schedule_for_date(target_date, OperatingSchedule.ScheduleType.REGULAR)


def get_temporary_operating_schedule_for_date(target_date: date):
    return _schedule_for_date(target_date, OperatingSchedule.ScheduleType.TEMPORARY)


def get_effective_operating_schedule_for_date(target_date: date):
    return get_temporary_operating_schedule_for_date(
        target_date
    ) or get_regular_operating_schedule_for_date(target_date)


def get_operating_day_for_date(target_date: date):
    schedule = get_effective_operating_schedule_for_date(target_date)
    if schedule is None:
        return None
    return (
        OperatingScheduleDay.objects.filter(
            schedule=schedule,
            weekday=target_date.weekday(),
        )
        .prefetch_related("windows")
        .first()
    )


def get_active_room_notices(
    *,
    at: datetime | None = None,
    target_date: date | None = None,
):
    current = at or timezone.now()
    notices = RoomNotice.objects.filter(
        is_active=True,
        effective_until__gte=timezone.localdate(current),
        visible_from__lte=current,
    ).filter(Q(visible_until__isnull=True) | Q(visible_until__gte=current))
    if target_date is not None:
        notices = notices.filter(
            effective_from__lte=target_date,
            effective_until__gte=target_date,
        )
    return notices.order_by("-visible_from", "-created_at")


def get_booking_policy_for_date(target_date: date):
    return (
        BookingPolicy.objects.filter(
            is_active=True,
            valid_from__lte=target_date,
        )
        .order_by("-valid_from", "-created_at")
        .first()
    )
