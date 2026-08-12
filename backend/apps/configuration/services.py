from datetime import date, datetime, time, timedelta

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.core.api.errors import (
    OperatingDayConfigurationInvalid,
    OperatingScheduleOverlap,
    OperatingScheduleRequired,
    OperatingScheduleStartInvalid,
    OperatingWindowInvalid,
    OperatingWindowOverlap,
    RoomNoticeInvalidPeriod,
    RoomNoticeMessageRequired,
    ScheduleChangeAffectsReservations,
    ScheduleReplacementInvalid,
    ShiftReplacementConflict,
    ShiftReplacementInvalid,
    TemporaryScheduleEndRequired,
)

from .calendar import (
    aware_at,
    interval_is_within_operating_day,
    lock_operating_date,
    resolve_operating_day,
)
from .models import (
    BookingPolicy,
    CalendarException,
    OperatingSchedule,
    OperatingScheduleDay,
    OperatingWindow,
    ReportConfiguration,
    RoomNotice,
    Shift,
    Weekday,
)

BOOKING_POLICY_FIELDS = (
    "cancellation_limit_minutes",
    "max_future_reservations_per_user",
)

REPORT_CONFIGURATION_FIELDS = (
    "default_format",
    "group_by_shift",
    "include_occurrences",
)


@transaction.atomic
def update_current_booking_policy(*, values: dict) -> BookingPolicy:
    today = timezone.localdate()
    policies = list(
        BookingPolicy.objects.select_for_update().order_by(
            "valid_from", "created_at", "pk"
        )
    )
    base = policies[-1] if policies else None

    if base and base.valid_from >= today and not base.reservations.exists():
        for field, value in values.items():
            setattr(base, field, value)
        base.save(update_fields=[*values.keys(), "updated_at"])
        return base

    merged = {
        field: values.get(
            field,
            getattr(base, field)
            if base
            else BookingPolicy._meta.get_field(field).default,
        )
        for field in BOOKING_POLICY_FIELDS
    }
    valid_from = (
        max(today, base.valid_from + timedelta(days=1))
        if base and base.valid_from >= today
        else today
    )

    if base and (base.valid_until is None or base.valid_until >= valid_from):
        base.valid_until = valid_from - timedelta(days=1)
        base.save(update_fields=["valid_until", "updated_at"])

    return BookingPolicy.objects.create(
        **merged,
        valid_from=valid_from,
    )


@transaction.atomic
def update_report_configuration(
    *,
    values: dict,
    actor_profile: str,
) -> ReportConfiguration:
    configuration = (
        ReportConfiguration.objects.select_for_update().filter(is_active=True).first()
    )
    old_values = (
        {field: getattr(configuration, field) for field in REPORT_CONFIGURATION_FIELDS}
        if configuration
        else {}
    )
    if configuration is None:
        configuration = ReportConfiguration.objects.create(**values)
    else:
        for field, value in values.items():
            setattr(configuration, field, value)
        configuration.save(update_fields=[*values.keys(), "updated_at"])
    AuditEvent.objects.create(
        actor_profile=actor_profile,
        action="REPORT_CONFIGURATION_UPDATED",
        entity_type="ReportConfiguration",
        entity_id=str(configuration.pk),
        old_values=old_values,
        new_values={
            field: getattr(configuration, field)
            for field in REPORT_CONFIGURATION_FIELDS
        },
    )
    return configuration


@transaction.atomic
def replace_shift(
    *,
    shift_id: int,
    effective_from: date,
    name: str,
    start_time: time,
    end_time: time,
    display_order: int,
    actor_profile: str,
) -> Shift:
    shift = Shift.objects.select_for_update().get(pk=shift_id)
    today = timezone.localdate()

    if (
        effective_from <= today
        or effective_from <= shift.valid_from
        or shift.valid_until is not None
    ):
        raise ShiftReplacementInvalid()

    conflicts = (
        Shift.objects.select_for_update()
        .filter(
            is_active=True,
            start_time__lt=end_time,
            end_time__gt=start_time,
        )
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=effective_from))
        .exclude(pk=shift.pk)
    )
    if conflicts.exists():
        raise ShiftReplacementConflict()

    old_values = {
        "name": shift.name,
        "start_time": shift.start_time.isoformat(),
        "end_time": shift.end_time.isoformat(),
        "display_order": shift.display_order,
        "valid_from": shift.valid_from.isoformat(),
        "valid_until": shift.valid_until.isoformat() if shift.valid_until else None,
    }
    shift.valid_until = effective_from - timedelta(days=1)
    shift.save(update_fields=["valid_until", "updated_at"])

    replacement = Shift.objects.create(
        series_key=shift.series_key,
        name=name,
        start_time=start_time,
        end_time=end_time,
        display_order=display_order,
        valid_from=effective_from,
    )
    AuditEvent.objects.create(
        actor_profile=actor_profile,
        action="SHIFT_REPLACED",
        entity_type="Shift",
        entity_id=str(shift.pk),
        old_values=old_values,
        new_values={
            "shift_id": replacement.pk,
            "name": replacement.name,
            "start_time": replacement.start_time.isoformat(),
            "end_time": replacement.end_time.isoformat(),
            "display_order": replacement.display_order,
            "valid_from": replacement.valid_from.isoformat(),
        },
    )
    return replacement


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


def _period_datetimes(
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


def _lock_reservable_dates(
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


def _reservations_for_period(
    *,
    valid_from: date,
    valid_until: date | None,
    lock: bool,
):
    from apps.operations.models import Reservation

    starts_at, ends_at = _period_datetimes(valid_from, valid_until)
    reservations = Reservation.objects.filter(
        status=Reservation.Status.CONFIRMED,
        starts_at__gte=starts_at,
    ).order_by("starts_at", "pk")
    if ends_at is not None:
        reservations = reservations.filter(starts_at__lt=ends_at)
    if lock:
        reservations = reservations.select_for_update()
    return list(reservations)


def _conflicts_under_effective_calendar(reservations) -> list:
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
    from .selectors import (
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
        for reservation in _reservations_for_period(
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


def preview_calendar_exception_impact(*, values: dict) -> dict:
    target_date = values["date"]
    reservations = _reservations_for_period(
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


def _cancel_conflicting_reservations(
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


def _validate_confirmed_schedule_impact(
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


def _notice_values_for_change(
    *,
    notice: dict,
    valid_from: date,
    valid_until: date | None,
    notice_type: str,
) -> dict:
    values = dict(notice)
    values.setdefault("notice_type", notice_type)
    values.setdefault("effective_from", valid_from)
    values.setdefault("effective_until", valid_until or valid_from)
    return values


def _deactivate_schedule_notices(
    *,
    schedule: OperatingSchedule,
    actor_profile: str,
) -> None:
    notice_ids = list(
        schedule.notices.filter(is_active=True).values_list("pk", flat=True)
    )
    for notice_id in notice_ids:
        update_room_notice(
            notice_id=notice_id,
            values={"is_active": False},
            actor_profile=actor_profile,
        )


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
    _lock_reservable_dates(valid_from=valid_from, valid_until=valid_until)
    if _schedule_overlap_exists(
        schedule_type=schedule_type,
        valid_from=valid_from,
        valid_until=valid_until,
    ):
        raise OperatingScheduleOverlap()
    reservations = _reservations_for_period(
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

    conflicts = _conflicts_under_effective_calendar(reservations)
    _validate_confirmed_schedule_impact(
        conflicts=conflicts,
        confirm_cancellation=confirm_cancellation,
        expected_conflict_ids=expected_conflict_ids,
    )
    cancellation_reason = reason.strip() or f"Alteração do calendário: {name}."
    _cancel_conflicting_reservations(
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
            values=_notice_values_for_change(
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
    _lock_reservable_dates(
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
    reservations = _reservations_for_period(
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
    conflicts = _conflicts_under_effective_calendar(reservations)
    _validate_confirmed_schedule_impact(
        conflicts=conflicts,
        confirm_cancellation=confirm_cancellation,
        expected_conflict_ids=expected_conflict_ids,
    )
    cancellation_reason = replacement.reason or (
        f"Substituição do calendário: {replacement.name}."
    )
    _cancel_conflicting_reservations(
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
    _deactivate_schedule_notices(
        schedule=schedule,
        actor_profile=actor_profile,
    )
    if notify_users:
        create_room_notice(
            values=_notice_values_for_change(
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
    _lock_reservable_dates(
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
    reservations = _reservations_for_period(
        valid_from=period_start,
        valid_until=period_end,
        lock=True,
    )
    for field, value in values.items():
        setattr(schedule, field, value)
    schedule.save(update_fields=[*values.keys(), "updated_at"])
    _replace_schedule_days(schedule, days)
    conflicts = _conflicts_under_effective_calendar(reservations)
    if conflicts and not confirm_cancellation:
        raise ScheduleChangeAffectsReservations(
            reservation.pk for reservation in conflicts
        )
    _cancel_conflicting_reservations(
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
    _deactivate_schedule_notices(
        schedule=schedule,
        actor_profile=actor_profile,
    )
    return OperatingSchedule.objects.prefetch_related("days__windows").get(
        pk=schedule.pk
    )


def _validate_notice_values(values: dict) -> None:
    if not str(values.get("message", "")).strip():
        raise RoomNoticeMessageRequired()
    if values["effective_until"] < values["effective_from"]:
        raise RoomNoticeInvalidPeriod()
    if values.get("visible_until") and values["visible_until"] < values["visible_from"]:
        raise RoomNoticeInvalidPeriod()


@transaction.atomic
def create_room_notice(
    *,
    values: dict,
    actor_profile: str,
    operating_schedule: OperatingSchedule | None = None,
    calendar_exception: CalendarException | None = None,
) -> RoomNotice:
    _validate_notice_values(values)
    room_notice = RoomNotice.objects.create(
        **values,
        created_by_profile=actor_profile,
        operating_schedule=operating_schedule,
        calendar_exception=calendar_exception,
    )
    AuditEvent.objects.create(
        actor_profile=actor_profile,
        action="ROOM_NOTICE_CREATED",
        entity_type="RoomNotice",
        entity_id=str(room_notice.pk),
        new_values={
            "title": room_notice.title,
            "notice_type": room_notice.notice_type,
            "effective_from": room_notice.effective_from.isoformat(),
            "effective_until": room_notice.effective_until.isoformat(),
            "is_active": room_notice.is_active,
        },
    )
    return room_notice


@transaction.atomic
def update_room_notice(
    *,
    notice_id: int,
    values: dict,
    actor_profile: str,
) -> RoomNotice:
    notice = RoomNotice.objects.select_for_update().get(pk=notice_id)
    old_values = {
        field: getattr(notice, field)
        for field in [
            "notice_type",
            "title",
            "message",
            "effective_from",
            "effective_until",
            "visible_from",
            "visible_until",
            "is_active",
        ]
    }
    merged = {**old_values, **values}
    _validate_notice_values(merged)
    for field, value in values.items():
        setattr(notice, field, value)
    notice.save(update_fields=[*values.keys(), "updated_at"])

    def serialize(value):
        return value.isoformat() if hasattr(value, "isoformat") else value

    AuditEvent.objects.create(
        actor_profile=actor_profile,
        action="ROOM_NOTICE_UPDATED",
        entity_type="RoomNotice",
        entity_id=str(notice.pk),
        old_values={key: serialize(value) for key, value in old_values.items()},
        new_values={key: serialize(value) for key, value in merged.items()},
    )
    return notice


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
    _lock_reservable_dates(valid_from=target_date, valid_until=target_date)
    if exception_id is not None:
        existing = CalendarException.objects.select_for_update().get(pk=exception_id)
    reservations = _reservations_for_period(
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
    conflicts = _conflicts_under_effective_calendar(reservations)
    _validate_confirmed_schedule_impact(
        conflicts=conflicts,
        confirm_cancellation=confirm_cancellation,
        expected_conflict_ids=expected_conflict_ids,
    )
    _cancel_conflicting_reservations(
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
            values=_notice_values_for_change(
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
