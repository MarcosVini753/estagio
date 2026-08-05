from datetime import date, datetime, timedelta

from django.db.models import Q

from apps.configuration.calendar import resolve_operating_day
from apps.configuration.models import Shift
from apps.occurrences.models import Occurrence
from apps.operations.models import ComputerAllocation, Reservation, UseSession


def get_sessions_for_period(starts_at: datetime, ends_at: datetime):
    return (
        UseSession.objects.filter(
            started_at__gte=starts_at,
            started_at__lt=ends_at,
        )
        .exclude(status=UseSession.Status.CANCELLED)
        .select_related("start_shift")
    )


def get_allocations_for_period(starts_at: datetime, ends_at: datetime):
    return (
        ComputerAllocation.objects.filter(
            started_at__lt=ends_at,
            session__status__in=[
                UseSession.Status.ACTIVE,
                UseSession.Status.FINISHED,
            ],
        )
        .filter(Q(ended_at__isnull=True) | Q(ended_at__gt=starts_at))
        .select_related("session")
    )


def get_reservations_for_period(starts_at: datetime, ends_at: datetime):
    return Reservation.objects.filter(
        starts_at__gte=starts_at,
        starts_at__lt=ends_at,
    )


def get_occurrences_for_period(starts_at: datetime, ends_at: datetime):
    return Occurrence.objects.filter(
        created_at__gte=starts_at,
        created_at__lt=ends_at,
    )


def get_shifts_for_period(starts_on: date, ends_on: date):
    return (
        Shift.objects.filter(valid_from__lt=ends_on)
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=starts_on))
        .order_by("display_order", "valid_from")
    )


def get_operating_days_for_period(starts_on: date, ends_on: date):
    current = starts_on
    results = []
    while current < ends_on:
        results.append(resolve_operating_day(current))
        current += timedelta(days=1)
    return results
