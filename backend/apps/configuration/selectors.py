from datetime import date

from django.db.models import Q

from .models import BookingPolicy, CalendarException, Shift


def get_shifts_for_date(target_date: date):
    return (
        Shift.objects.filter(is_active=True, valid_from__lte=target_date)
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=target_date))
        .order_by("display_order", "start_time")
    )


def get_calendar_exception_for_date(target_date: date):
    return CalendarException.objects.filter(date=target_date).first()


def get_booking_policy_for_date(target_date: date):
    return (
        BookingPolicy.objects.filter(
            is_active=True,
            valid_from__lte=target_date,
        )
        .order_by("-valid_from", "-created_at")
        .first()
    )
