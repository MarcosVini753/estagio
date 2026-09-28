from datetime import date, datetime, timedelta

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.core.api.errors import (
    OperatingDayConfigurationInvalid,
    OperatingScheduleOverlap,
    OperatingScheduleStartInvalid,
    OperatingWindowInvalid,
    OperatingWindowOverlap,
    ScheduleChangeAffectsReservations,
    ScheduleReplacementInvalid,
    TemporaryScheduleEndRequired,
)

from ..models import (
    OperatingSchedule,
    OperatingScheduleDay,
    OperatingWindow,
    RoomNotice,
    Weekday,
)
from ._impact import (
    cancel_conflicting_reservations,
    conflicts_under_effective_calendar,
    lock_reservable_dates,
    reservations_for_period,
    validate_confirmed_schedule_impact,
)
from .notices import (
    create_room_notice,
    deactivate_schedule_notices,
    notice_values_for_change,
)


def validate_schedule_days(days: list[dict]) -> list[dict]:
    if len(days) != 7 or {day.get("weekday") for day in days} != set(Weekday.values):
        raise OperatingDayConfigurationInvalid(
            "O calendário deve configurar exatamente os sete dias, sem repetição."
        )

    normalized = []
    for day in sorted(days, key=lambda item: item["weekday"]):
        windows = sorted(
            day.get("windows", []),
            key=lambda item: (item["opens_at"], item["closes_at"]),
        )
        if day["is_open"] and not windows:
            raise OperatingDayConfigurationInvalid(
                "Todo dia aberto deve possuir ao menos uma janela."
            )
        if not day["is_open"] and windows:
            raise OperatingDayConfigurationInvalid(
                "Dia fechado não pode possuir janelas."
            )
        previous_closes_at = None
        normalized_windows = []
        for display_order, window in enumerate(windows):
            if window["opens_at"] >= window["closes_at"]:
                raise OperatingWindowInvalid()
            if previous_closes_at and window["opens_at"] < previous_closes_at:
                raise OperatingWindowOverlap()
            normalized_windows.append(
                {
                    "opens_at": window["opens_at"],
                    "closes_at": window["closes_at"],
                    "display_order": window.get("display_order", display_order),
                }
            )
            previous_closes_at = window["closes_at"]
        normalized.append(
            {
                "weekday": day["weekday"],
                "is_open": day["is_open"],
                "windows": normalized_windows,
            }
        )
    return normalized


def _schedule_overlap_exists(
    *,
    schedule_type: str,
    valid_from: date,
    valid_until: date | None,
    exclude_schedule_id: int | None = None,
) -> bool:
    schedules = OperatingSchedule.objects.select_for_update().filter(
        schedule_type=schedule_type,
        is_active=True,
    )
    if exclude_schedule_id is not None:
        schedules = schedules.exclude(pk=exclude_schedule_id)
    schedules = schedules.filter(
        Q(valid_until__isnull=True) | Q(valid_until__gte=valid_from)
    )
    if valid_until is not None:
        schedules = schedules.filter(valid_from__lte=valid_until)
    return schedules.exists()


def _validate_schedule_period(
    *,
    schedule_type: str,
    valid_from: date,
    valid_until: date | None,
) -> None:
    if valid_from <= timezone.localdate():
        raise OperatingScheduleStartInvalid()
    if valid_until is not None and valid_until < valid_from:
        raise ScheduleReplacementInvalid(
            "A validade final não pode anteceder a inicial."
        )
    if (
        schedule_type == OperatingSchedule.ScheduleType.TEMPORARY
        and valid_until is None
    ):
        raise TemporaryScheduleEndRequired()


def _create_schedule_days(
    schedule: OperatingSchedule,
    days: list[dict],
) -> None:
    for day_data in days:
        windows = day_data["windows"]
        day = OperatingScheduleDay.objects.create(
            schedule=schedule,
            weekday=day_data["weekday"],
            is_open=day_data["is_open"],
        )
        OperatingWindow.objects.bulk_create(
            [
                OperatingWindow(schedule_day=day, **window_data)
                for window_data in windows
            ]
        )


def _replace_schedule_days(
    schedule: OperatingSchedule,
    days: list[dict],
) -> None:
    schedule.days.all().delete()
    _create_schedule_days(schedule, days)


def _schedule_days_payload(schedule: OperatingSchedule) -> list[dict]:
    return [
        {
            "weekday": day.weekday,
            "is_open": day.is_open,
            "windows": [
                {
                    "opens_at": window.opens_at,
                    "closes_at": window.closes_at,
                    "display_order": window.display_order,
                }
                for window in day.windows.all()
            ],
        }
        for day in schedule.days.all()
    ]


def _schedule_snapshot(schedule: OperatingSchedule) -> dict:
    schedule = OperatingSchedule.objects.prefetch_related("days__windows").get(
        pk=schedule.pk
    )
    return {
        "id": schedule.pk,
        "series_key": str(schedule.series_key),
        "name": schedule.name,
        "schedule_type": schedule.schedule_type,
        "valid_from": schedule.valid_from.isoformat(),
        "valid_until": (
            schedule.valid_until.isoformat() if schedule.valid_until else None
        ),
        "reason": schedule.reason,
        "is_active": schedule.is_active,
        "days": [
            {
                "weekday": day.weekday,
                "is_open": day.is_open,
                "windows": [
                    {
                        "opens_at": window.opens_at.isoformat(),
                        "closes_at": window.closes_at.isoformat(),
                    }
                    for window in day.windows.all()
                ],
            }
            for day in schedule.days.all()
        ],
    }


def _proposal_windows(days: list[dict], target_date: date):
    day = next(day for day in days if day["weekday"] == target_date.weekday())
    if not day["is_open"]:
        return []
    zone = timezone.get_current_timezone()
    return [
        (
            timezone.make_aware(
                datetime.combine(target_date, window["opens_at"]), zone
            ),
            timezone.make_aware(
                datetime.combine(target_date, window["closes_at"]), zone
            ),
        )
        for window in day["windows"]
    ]


def _reservation_conflicts_with_proposal(
    *,
    reservation,
    schedule_type: str,
    days: list[dict],
) -> bool:
    from ..selectors import (
        get_calendar_exception_for_date,
        get_temporary_operating_schedule_for_date,
    )

    target_date = timezone.localdate(reservation.starts_at)
    if get_calendar_exception_for_date(target_date) is not None:
        return False
    if (
        schedule_type == OperatingSchedule.ScheduleType.REGULAR
        and get_temporary_operating_schedule_for_date(target_date) is not None
    ):
        return False
    return not any(
        starts_at <= reservation.starts_at and reservation.ends_at <= ends_at
        for starts_at, ends_at in _proposal_windows(days, target_date)
    )


def preview_operating_schedule_impact(
    *,
    schedule_type: str,
    valid_from: date,
    valid_until: date | None,
    days: list[dict],
) -> dict:
    _validate_schedule_period(
        schedule_type=schedule_type,
        valid_from=valid_from,
        valid_until=valid_until,
    )
    normalized_days = validate_schedule_days(days)
    conflicts = [
        reservation
        for reservation in reservations_for_period(
            valid_from=valid_from,
            valid_until=valid_until,
            lock=False,
        )
        if _reservation_conflicts_with_proposal(
            reservation=reservation,
            schedule_type=schedule_type,
            days=normalized_days,
        )
    ]
    return {
        "affected_period": {
            "starts_on": valid_from,
            "ends_on": valid_until,
        },
        "conflicting_reservations": [
            {
                "id": reservation.pk,
                "user_reference": reservation.user_reference,
                "computer_id": reservation.computer_id,
                "starts_at": reservation.starts_at,
                "ends_at": reservation.ends_at,
                "reason": "OUTSIDE_NEW_OPERATING_HOURS",
            }
            for reservation in conflicts
        ],
        "total": len(conflicts),
    }


@transaction.atomic
def create_operating_schedule(
    *,
    name: str,
    schedule_type: str,
    valid_from: date,
    valid_until: date | None,
    reason: str,
    days: list[dict],
    actor_profile: str,
    confirm_cancellation: bool = False,
    notify_users: bool = False,
    notice: dict | None = None,
    expected_conflict_ids: list[int] | None = None,
) -> OperatingSchedule:
    _validate_schedule_period(
        schedule_type=schedule_type,
        valid_from=valid_from,
        valid_until=valid_until,
    )
    normalized_days = validate_schedule_days(days)
    lock_reservable_dates(valid_from=valid_from, valid_until=valid_until)
    if _schedule_overlap_exists(
        schedule_type=schedule_type,
        valid_from=valid_from,
        valid_until=valid_until,
    ):
        raise OperatingScheduleOverlap()
    reservations = reservations_for_period(
        valid_from=valid_from,
        valid_until=valid_until,
        lock=True,
    )
    try:
        with transaction.atomic():
            schedule = OperatingSchedule.objects.create(
                name=name,
                schedule_type=schedule_type,
                valid_from=valid_from,
                valid_until=valid_until,
                reason=reason.strip(),
                created_by_profile=actor_profile,
            )
            _create_schedule_days(schedule, normalized_days)
    except IntegrityError as error:
        raise OperatingScheduleOverlap() from error

    conflicts = conflicts_under_effective_calendar(reservations)
    validate_confirmed_schedule_impact(
        conflicts=conflicts,
        confirm_cancellation=confirm_cancellation,
        expected_conflict_ids=expected_conflict_ids,
    )
    cancellation_reason = reason.strip() or f"Alteração do calendário: {name}."
    cancel_conflicting_reservations(
        conflicts=conflicts,
        actor_profile=actor_profile,
        reason=cancellation_reason,
    )
    AuditEvent.objects.create(
        actor_profile=actor_profile,
        action="OPERATING_SCHEDULE_CREATED",
        entity_type="OperatingSchedule",
        entity_id=str(schedule.pk),
        new_values=_schedule_snapshot(schedule),
        reason=reason.strip(),
    )
    if notify_users:
        create_room_notice(
            values=notice_values_for_change(
                notice=notice or {},
                valid_from=valid_from,
                valid_until=valid_until,
                notice_type=RoomNotice.NoticeType.SCHEDULE_CHANGE,
            ),
            actor_profile=actor_profile,
            operating_schedule=schedule,
        )
    return OperatingSchedule.objects.prefetch_related("days__windows").get(
        pk=schedule.pk
    )


@transaction.atomic
def replace_operating_schedule(
    *,
    schedule_id: int,
    effective_from: date,
    actor_profile: str,
    name: str | None = None,
    reason: str | None = None,
    days: list[dict] | None = None,
    confirm_cancellation: bool = False,
    notify_users: bool = False,
    notice: dict | None = None,
    expected_conflict_ids: list[int] | None = None,
) -> OperatingSchedule:
    lock_reservable_dates(
        valid_from=effective_from,
        valid_until=None,
    )
    schedule = (
        OperatingSchedule.objects.select_for_update()
        .prefetch_related("days__windows")
        .get(pk=schedule_id)
    )
    if (
        not schedule.is_active
        or effective_from <= timezone.localdate()
        or effective_from <= schedule.valid_from
        or (schedule.valid_until and effective_from > schedule.valid_until)
    ):
        raise ScheduleReplacementInvalid()
    replacement_until = schedule.valid_until
    replacement_days = validate_schedule_days(
        days if days is not None else _schedule_days_payload(schedule)
    )
    if _schedule_overlap_exists(
        schedule_type=schedule.schedule_type,
        valid_from=effective_from,
        valid_until=replacement_until,
        exclude_schedule_id=schedule.pk,
    ):
        raise OperatingScheduleOverlap()
    reservations = reservations_for_period(
        valid_from=effective_from,
        valid_until=replacement_until,
        lock=True,
    )
    old_snapshot = _schedule_snapshot(schedule)
    schedule.valid_until = effective_from - timedelta(days=1)
    schedule.save(update_fields=["valid_until", "updated_at"])
    replacement = OperatingSchedule.objects.create(
        series_key=schedule.series_key,
        name=name or schedule.name,
        schedule_type=schedule.schedule_type,
        valid_from=effective_from,
        valid_until=replacement_until,
        reason=(reason if reason is not None else schedule.reason).strip(),
        created_by_profile=actor_profile,
    )
    _create_schedule_days(replacement, replacement_days)
    conflicts = conflicts_under_effective_calendar(reservations)
    validate_confirmed_schedule_impact(
        conflicts=conflicts,
        confirm_cancellation=confirm_cancellation,
        expected_conflict_ids=expected_conflict_ids,
    )
    cancellation_reason = replacement.reason or (
        f"Substituição do calendário: {replacement.name}."
    )
    cancel_conflicting_reservations(
        conflicts=conflicts,
        actor_profile=actor_profile,
        reason=cancellation_reason,
    )
    AuditEvent.objects.create(
        actor_profile=actor_profile,
        action="OPERATING_SCHEDULE_REPLACED",
        entity_type="OperatingSchedule",
        entity_id=str(schedule.pk),
        old_values=old_snapshot,
        new_values=_schedule_snapshot(replacement),
        reason=replacement.reason,
    )
    deactivate_schedule_notices(
        schedule=schedule,
        actor_profile=actor_profile,
    )
    if notify_users:
        create_room_notice(
            values=notice_values_for_change(
                notice=notice or {},
                valid_from=effective_from,
                valid_until=replacement_until,
                notice_type=RoomNotice.NoticeType.SCHEDULE_CHANGE,
            ),
            actor_profile=actor_profile,
            operating_schedule=replacement,
        )
    return OperatingSchedule.objects.prefetch_related("days__windows").get(
        pk=replacement.pk
    )


@transaction.atomic
def update_future_operating_schedule(
    *,
    schedule_id: int,
    values: dict,
    actor_profile: str,
    confirm_cancellation: bool = False,
) -> OperatingSchedule:
    values = dict(values)
    schedule_preview = OperatingSchedule.objects.get(pk=schedule_id)
    preview_valid_from = values.get("valid_from", schedule_preview.valid_from)
    preview_valid_until = values.get("valid_until", schedule_preview.valid_until)
    lock_reservable_dates(
        valid_from=min(schedule_preview.valid_from, preview_valid_from),
        valid_until=(
            max(schedule_preview.valid_until, preview_valid_until)
            if schedule_preview.valid_until and preview_valid_until
            else None
        ),
    )
    schedule = (
        OperatingSchedule.objects.select_for_update()
        .prefetch_related("days__windows")
        .get(pk=schedule_id)
    )
    if schedule.valid_from <= timezone.localdate():
        raise ScheduleReplacementInvalid(
            "Calendário já iniciado deve ser substituído por uma nova versão."
        )
    old_snapshot = _schedule_snapshot(schedule)
    days = validate_schedule_days(
        values.pop("days") if "days" in values else _schedule_days_payload(schedule)
    )
    proposed = {
        "schedule_type": values.get("schedule_type", schedule.schedule_type),
        "valid_from": values.get("valid_from", schedule.valid_from),
        "valid_until": values.get("valid_until", schedule.valid_until),
    }
    _validate_schedule_period(**proposed)
    if values.get("is_active", schedule.is_active) and _schedule_overlap_exists(
        **proposed,
        exclude_schedule_id=schedule.pk,
    ):
        raise OperatingScheduleOverlap()
    period_start = min(schedule.valid_from, proposed["valid_from"])
    candidate_ends = [
        item for item in [schedule.valid_until, proposed["valid_until"]] if item
    ]
    period_end = max(candidate_ends) if len(candidate_ends) == 2 else None
    reservations = reservations_for_period(
        valid_from=period_start,
        valid_until=period_end,
        lock=True,
    )
    for field, value in values.items():
        setattr(schedule, field, value)
    schedule.save(update_fields=[*values.keys(), "updated_at"])
    _replace_schedule_days(schedule, days)
    conflicts = conflicts_under_effective_calendar(reservations)
    if conflicts and not confirm_cancellation:
        raise ScheduleChangeAffectsReservations(
            reservation.pk for reservation in conflicts
        )
    cancel_conflicting_reservations(
        conflicts=conflicts,
        actor_profile=actor_profile,
        reason=schedule.reason or f"Alteração do calendário: {schedule.name}.",
    )
    AuditEvent.objects.create(
        actor_profile=actor_profile,
        action="OPERATING_SCHEDULE_UPDATED",
        entity_type="OperatingSchedule",
        entity_id=str(schedule.pk),
        old_values=old_snapshot,
        new_values=_schedule_snapshot(schedule),
        reason=schedule.reason,
    )
    deactivate_schedule_notices(
        schedule=schedule,
        actor_profile=actor_profile,
    )
    return OperatingSchedule.objects.prefetch_related("days__windows").get(
        pk=schedule.pk
    )


__all__ = [
    "create_operating_schedule",
    "preview_operating_schedule_impact",
    "replace_operating_schedule",
    "update_future_operating_schedule",
    "validate_schedule_days",
]
