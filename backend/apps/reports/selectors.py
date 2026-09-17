from dataclasses import dataclass
from datetime import date, datetime, timedelta

from django.db.models import Prefetch, Q

from apps.computers.models import Computer, ComputerOperationalStateChange
from apps.configuration.calendar import resolve_operating_day_from_sources
from apps.configuration.models import CalendarException, OperatingSchedule, Shift
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
        .select_related("session", "session__start_shift", "computer")
    )


def get_reservations_for_period(starts_at: datetime, ends_at: datetime):
    return Reservation.objects.filter(
        starts_at__gte=starts_at,
        starts_at__lt=ends_at,
    ).select_related("computer")


def get_occurrences_for_period(starts_at: datetime, ends_at: datetime):
    return Occurrence.objects.filter(
        created_at__gte=starts_at,
        created_at__lt=ends_at,
    ).select_related("computer")


def get_shifts_for_period(starts_on: date, ends_on: date):
    return (
        Shift.objects.filter(valid_from__lt=ends_on)
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=starts_on))
        .order_by("display_order", "valid_from")
    )


def get_operating_days_for_period(starts_on: date, ends_on: date):
    exceptions_by_date = {
        exception.date: exception
        for exception in CalendarException.objects.filter(
            date__gte=starts_on,
            date__lt=ends_on,
        )
    }
    schedules = list(
        OperatingSchedule.objects.filter(
            is_active=True,
            valid_from__lt=ends_on,
        )
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=starts_on))
        .prefetch_related("days__windows")
        .order_by("-valid_from", "-created_at")
    )

    def effective_schedule(target_date):
        def first_applicable(schedule_type):
            return next(
                (
                    schedule
                    for schedule in schedules
                    if schedule.schedule_type == schedule_type
                    and schedule.valid_from <= target_date
                    and (
                        schedule.valid_until is None
                        or schedule.valid_until >= target_date
                    )
                ),
                None,
            )

        return first_applicable(
            OperatingSchedule.ScheduleType.TEMPORARY
        ) or first_applicable(OperatingSchedule.ScheduleType.REGULAR)

    current = starts_on
    results = []
    while current < ends_on:
        results.append(
            resolve_operating_day_from_sources(
                current,
                exception=exceptions_by_date.get(current),
                schedule=effective_schedule(current),
            )
        )
        current += timedelta(days=1)
    return results


def get_computers_for_period(ends_at: datetime):
    state_changes = ComputerOperationalStateChange.objects.order_by(
        "changed_at",
        "pk",
    )
    return Computer.objects.filter(created_at__lt=ends_at).prefetch_related(
        Prefetch(
            "operational_state_changes",
            queryset=state_changes,
            to_attr="report_state_changes",
        )
    )


@dataclass(frozen=True)
class ReportData:
    sessions: list
    allocations: list
    reservations: list
    occurrences: list
    shifts: list
    operating_days: list
    computers: list


def load_report_data(
    *,
    starts_at: datetime,
    ends_at: datetime,
    starts_on: date,
    ends_on: date,
) -> ReportData:
    return ReportData(
        sessions=list(get_sessions_for_period(starts_at, ends_at)),
        allocations=list(get_allocations_for_period(starts_at, ends_at)),
        reservations=list(get_reservations_for_period(starts_at, ends_at)),
        occurrences=list(get_occurrences_for_period(starts_at, ends_at)),
        shifts=list(get_shifts_for_period(starts_on, ends_on)),
        operating_days=get_operating_days_for_period(starts_on, ends_on),
        computers=list(get_computers_for_period(ends_at)),
    )
