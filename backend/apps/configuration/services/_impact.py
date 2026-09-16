from datetime import date, datetime, time, timedelta

from django.utils import timezone

from apps.core.api.errors import (
    OperatingScheduleRequired,
    ScheduleChangeAffectsReservations,
)

from ..calendar import (
    interval_is_within_operating_day,
    lock_operating_date,
    resolve_operating_day,
)


def period_datetimes(
    valid_from: date,
    valid_until: date | None,
) -> tuple[datetime, datetime | None]:
    zone = timezone.get_current_timezone()
    starts_at = timezone.make_aware(datetime.combine(valid_from, time.min), zone)
    ends_at = (
        timezone.make_aware(
            datetime.combine(valid_until + timedelta(days=1), time.min), zone
        )
        if valid_until
        else None
    )
    return starts_at, ends_at


def lock_reservable_dates(
    *,
    valid_from: date,
    valid_until: date | None,
) -> None:
    today = timezone.localdate()
    for target_date in (today, today + timedelta(days=1)):
        if target_date >= valid_from and (
            valid_until is None or target_date <= valid_until
        ):
            lock_operating_date(target_date)


def reservations_for_period(
    *,
    valid_from: date,
    valid_until: date | None,
    lock: bool,
):
    from apps.operations.models import Reservation

    starts_at, ends_at = period_datetimes(valid_from, valid_until)
    reservations = Reservation.objects.filter(
        status=Reservation.Status.CONFIRMED,
        starts_at__gte=starts_at,
    ).order_by("starts_at", "pk")
    if ends_at is not None:
        reservations = reservations.filter(starts_at__lt=ends_at)
    if lock:
        reservations = reservations.select_for_update()
    return list(reservations)


def conflicts_under_effective_calendar(reservations) -> list:
    conflicts = []
    for reservation in reservations:
        target_date = timezone.localdate(reservation.starts_at)
        try:
            operating_day = resolve_operating_day(target_date)
        except OperatingScheduleRequired:
            conflicts.append(reservation)
            continue
        if not interval_is_within_operating_day(
            operating_day,
            reservation.starts_at,
            reservation.ends_at,
        ):
            conflicts.append(reservation)
    return conflicts


def cancel_conflicting_reservations(
    *,
    conflicts,
    actor_profile: str,
    reason: str,
) -> None:
    from apps.operations.services.reservations import (
        cancel_reservation_due_to_operational_change,
    )

    for reservation in conflicts:
        cancel_reservation_due_to_operational_change(
            reservation_id=reservation.pk,
            actor_profile=actor_profile,
            reason=reason,
        )


def validate_confirmed_schedule_impact(
    *,
    conflicts,
    confirm_cancellation: bool,
    expected_conflict_ids: list[int] | None,
) -> None:
    conflict_ids = [reservation.pk for reservation in conflicts]
    if expected_conflict_ids is not None and set(conflict_ids) != set(
        expected_conflict_ids
    ):
        raise ScheduleChangeAffectsReservations(conflict_ids)
    if conflicts and not confirm_cancellation:
        raise ScheduleChangeAffectsReservations(conflict_ids)


__all__ = [
    "cancel_conflicting_reservations",
    "conflicts_under_effective_calendar",
    "lock_reservable_dates",
    "reservations_for_period",
    "validate_confirmed_schedule_impact",
]
