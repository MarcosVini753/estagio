from datetime import date

from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.core.api.errors import CalendarExceptionDateInvalid

from ..calendar import aware_at
from ..models import CalendarException, RoomNotice
from ._impact import (
    cancel_conflicting_reservations,
    conflicts_under_effective_calendar,
    lock_reservable_dates,
    reservations_for_period,
    validate_confirmed_schedule_impact,
)
from .notices import create_room_notice, notice_values_for_change


def preview_calendar_exception_impact(*, values: dict) -> dict:
    target_date = values["date"]
    validate_calendar_exception_date(target_date)
    reservations = reservations_for_period(
        valid_from=target_date,
        valid_until=target_date,
        lock=False,
    )
    if values["exception_type"] == CalendarException.ExceptionType.CLOSED:
        conflicts = reservations
    else:
        starts_at = aware_at(target_date, values["opens_at"])
        ends_at = aware_at(target_date, values["closes_at"])
        conflicts = [
            reservation
            for reservation in reservations
            if not (
                starts_at <= reservation.starts_at and reservation.ends_at <= ends_at
            )
        ]
    return {
        "affected_period": {
            "starts_on": target_date,
            "ends_on": target_date,
        },
        "conflicting_reservations": [
            {
                "id": reservation.pk,
                "user_reference": reservation.user_reference,
                "computer_id": reservation.computer_id,
                "starts_at": reservation.starts_at,
                "ends_at": reservation.ends_at,
                "reason": "OUTSIDE_EXCEPTION_HOURS",
            }
            for reservation in conflicts
        ],
        "total": len(conflicts),
    }


def validate_calendar_exception_date(target_date: date) -> None:
    if target_date < timezone.localdate():
        raise CalendarExceptionDateInvalid()


@transaction.atomic
def apply_calendar_exception(
    *,
    values: dict,
    actor_profile: str,
    exception_id: int | None = None,
    confirm_cancellation: bool = False,
    notify_users: bool = False,
    notice: dict | None = None,
    expected_conflict_ids: list[int] | None = None,
) -> CalendarException:
    existing = None
    existing_preview = (
        CalendarException.objects.get(pk=exception_id)
        if exception_id is not None
        else None
    )
    target_date = values.get(
        "date",
        existing_preview.date if existing_preview else None,
    )
    validate_calendar_exception_date(target_date)
    lock_reservable_dates(valid_from=target_date, valid_until=target_date)
    if exception_id is not None:
        existing = CalendarException.objects.select_for_update().get(pk=exception_id)
    reservations = reservations_for_period(
        valid_from=target_date,
        valid_until=target_date,
        lock=True,
    )
    old_values = (
        {
            "date": existing.date.isoformat(),
            "exception_type": existing.exception_type,
            "opens_at": existing.opens_at.isoformat() if existing.opens_at else None,
            "closes_at": (
                existing.closes_at.isoformat() if existing.closes_at else None
            ),
            "description": existing.description,
        }
        if existing
        else {}
    )
    exception = existing or CalendarException()
    for field, value in values.items():
        setattr(exception, field, value)
    exception.full_clean()
    exception.save()
    conflicts = conflicts_under_effective_calendar(reservations)
    validate_confirmed_schedule_impact(
        conflicts=conflicts,
        confirm_cancellation=confirm_cancellation,
        expected_conflict_ids=expected_conflict_ids,
    )
    cancel_conflicting_reservations(
        conflicts=conflicts,
        actor_profile=actor_profile,
        reason=exception.description or "Alteração excepcional do funcionamento.",
    )
    AuditEvent.objects.create(
        actor_profile=actor_profile,
        action=(
            "CALENDAR_EXCEPTION_UPDATED" if existing else "CALENDAR_EXCEPTION_CREATED"
        ),
        entity_type="CalendarException",
        entity_id=str(exception.pk),
        old_values=old_values,
        new_values={
            "date": exception.date.isoformat(),
            "exception_type": exception.exception_type,
            "opens_at": exception.opens_at.isoformat() if exception.opens_at else None,
            "closes_at": (
                exception.closes_at.isoformat() if exception.closes_at else None
            ),
            "description": exception.description,
        },
        reason=exception.description,
    )
    if notify_users:
        create_room_notice(
            values=notice_values_for_change(
                notice=notice or {},
                valid_from=exception.date,
                valid_until=exception.date,
                notice_type=(
                    RoomNotice.NoticeType.SPECIAL_HOURS
                    if exception.exception_type
                    == CalendarException.ExceptionType.SPECIAL_HOURS
                    else RoomNotice.NoticeType.CLOSURE
                ),
            ),
            actor_profile=actor_profile,
            calendar_exception=exception,
        )
    return exception


__all__ = ["apply_calendar_exception", "preview_calendar_exception_impact"]
