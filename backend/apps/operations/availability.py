from collections import defaultdict
from datetime import date, datetime, time, timedelta

from django.db.models import Q
from django.utils import timezone

from apps.computers.models import Computer
from apps.configuration.models import CalendarException
from apps.configuration.selectors import (
    get_booking_policy_for_date,
    get_calendar_exception_for_date,
    get_shifts_for_date,
)
from apps.core.api.errors import ConfigurationRequired, DateOutsideAllowedWindow
from apps.operations.models import ComputerAllocation, Reservation

OCCUPIED = "OCCUPIED"
RESERVED = "RESERVED"
BLOCKING_RESERVATION_STATUSES = [Reservation.Status.CONFIRMED]


def validate_target_date(target_date: date, *, now=None) -> date:
    current = now or timezone.now()
    today = timezone.localdate(current)
    if target_date not in {today, today + timedelta(days=1)}:
        raise DateOutsideAllowedWindow()
    return today


def _aware(target_date: date, target_time: time) -> datetime:
    value = datetime.combine(target_date, target_time)
    return timezone.make_aware(value, timezone.get_current_timezone())


def get_operating_windows(target_date: date) -> list[tuple[datetime, datetime]]:
    exception = get_calendar_exception_for_date(target_date)
    if exception and exception.exception_type in {
        CalendarException.ExceptionType.CLOSED,
        CalendarException.ExceptionType.OPTIONAL_HOLIDAY,
    }:
        return []

    if exception and exception.exception_type == CalendarException.ExceptionType.SPECIAL_HOURS:
        if not exception.opens_at or not exception.closes_at:
            return []
        return [
            (
                _aware(target_date, exception.opens_at),
                _aware(target_date, exception.closes_at),
            )
        ]

    return [
        (
            _aware(target_date, shift.start_time),
            _aware(target_date, shift.end_time),
        )
        for shift in get_shifts_for_date(target_date)
    ]


def generate_slot_intervals(
    target_date: date,
) -> tuple[int, list[tuple[datetime, datetime]], list[tuple[datetime, datetime]]]:
    policy = get_booking_policy_for_date(target_date)
    if not policy:
        raise ConfigurationRequired("Nenhuma política de reservas está ativa para a data.")

    windows = get_operating_windows(target_date)
    duration = timedelta(minutes=policy.slot_duration_minutes)
    slots = []
    for window_start, window_end in windows:
        cursor = window_start
        while cursor + duration <= window_end:
            slots.append((cursor, cursor + duration))
            cursor += duration
    return policy.slot_duration_minutes, windows, slots


def _overlaps(
    interval_start: datetime,
    interval_end: datetime,
    event_start: datetime,
    event_end: datetime | None,
) -> bool:
    return event_start < interval_end and (
        event_end is None or event_end > interval_start
    )


def _load_events(
    computers: list[Computer],
    target_date: date,
    windows: list[tuple[datetime, datetime]],
    *,
    now: datetime,
):
    allocations_by_computer = defaultdict(list)
    reservations_by_computer = defaultdict(list)
    if not computers:
        return allocations_by_computer, reservations_by_computer

    day_start = _aware(target_date, time.min)
    day_end = day_start + timedelta(days=1)
    range_start = windows[0][0] if windows else day_start
    range_end = windows[-1][1] if windows else day_end
    if target_date == timezone.localdate(now):
        range_start = min(range_start, now)
        range_end = max(range_end, now + timedelta(minutes=1))

    computer_ids = [computer.pk for computer in computers]
    allocations = (
        ComputerAllocation.objects.filter(
            computer_id__in=computer_ids,
            started_at__lt=range_end,
        )
        .filter(Q(ended_at__isnull=True) | Q(ended_at__gt=range_start))
        .only("computer_id", "started_at", "ended_at")
    )
    for allocation in allocations:
        allocations_by_computer[allocation.computer_id].append(allocation)

    reservations = Reservation.objects.filter(
        computer_id__in=computer_ids,
        status__in=BLOCKING_RESERVATION_STATUSES,
        starts_at__lt=range_end,
        ends_at__gt=range_start,
    ).only("computer_id", "starts_at", "ends_at", "user_reference")
    for reservation in reservations:
        reservations_by_computer[reservation.computer_id].append(reservation)

    return allocations_by_computer, reservations_by_computer


def _effective_status(
    computer: Computer,
    interval_start: datetime,
    interval_end: datetime,
    allocations,
    reservations,
) -> str:
    if computer.operational_state == Computer.OperationalState.INACTIVE:
        return Computer.OperationalState.INACTIVE
    if computer.operational_state == Computer.OperationalState.MAINTENANCE:
        return Computer.OperationalState.MAINTENANCE
    if any(
        _overlaps(
            interval_start,
            interval_end,
            allocation.started_at,
            allocation.ended_at,
        )
        for allocation in allocations
    ):
        return OCCUPIED
    if any(
        _overlaps(
            interval_start,
            interval_end,
            reservation.starts_at,
            reservation.ends_at,
        )
        for reservation in reservations
    ):
        return RESERVED
    return Computer.OperationalState.AVAILABLE


def _reserved_by_user(
    interval_start: datetime,
    interval_end: datetime,
    reservations,
    user_reference: str | None,
) -> bool:
    if not user_reference:
        return False
    return any(
        reservation.user_reference == user_reference
        and _overlaps(
            interval_start,
            interval_end,
            reservation.starts_at,
            reservation.ends_at,
        )
        for reservation in reservations
    )


def _computer_slots(
    computer: Computer,
    slots: list[tuple[datetime, datetime]],
    allocations,
    reservations,
    *,
    is_today: bool,
    now: datetime,
    user_reference: str | None,
):
    payload = []
    for starts_at, ends_at in slots:
        status = _effective_status(
            computer,
            starts_at,
            ends_at,
            allocations,
            reservations,
        )
        reserved_by_current_user = _reserved_by_user(
            starts_at,
            ends_at,
            reservations,
            user_reference,
        )
        is_past = is_today and starts_at <= now
        payload.append(
            {
                "starts_at": starts_at,
                "ends_at": ends_at,
                "effective_status": status,
                "reserved_by_current_user": reserved_by_current_user,
                "selectable": not is_past
                and status == Computer.OperationalState.AVAILABLE,
            }
        )
    return payload


def get_computers_availability(
    *,
    target_date: date,
    computers,
    user_reference: str | None,
    now=None,
):
    current = now or timezone.now()
    today = validate_target_date(target_date, now=current)
    is_today = target_date == today
    duration, windows, intervals = generate_slot_intervals(target_date)
    computer_list = list(computers)
    allocations, reservations = _load_events(
        computer_list,
        target_date,
        windows,
        now=current,
    )

    items = []
    slots_by_computer = {}
    for computer in computer_list:
        computer_allocations = allocations[computer.pk]
        computer_reservations = reservations[computer.pk]
        slots = _computer_slots(
            computer,
            intervals,
            computer_allocations,
            computer_reservations,
            is_today=is_today,
            now=current,
            user_reference=user_reference,
        )
        slots_by_computer[computer.pk] = slots
        selectable = [slot for slot in slots if slot["selectable"]]

        status_now = None
        can_start_now = False
        if is_today:
            status_now = _effective_status(
                computer,
                current,
                current + timedelta(minutes=1),
                computer_allocations,
                computer_reservations,
            )
            reserved_by_user = _reserved_by_user(
                current,
                current + timedelta(minutes=1),
                computer_reservations,
                user_reference,
            )
            is_open = any(start <= current < end for start, end in windows)
            can_start_now = is_open and (
                status_now == Computer.OperationalState.AVAILABLE
                or (status_now == RESERVED and reserved_by_user)
            )

        next_slot = None
        if selectable:
            next_slot = {
                "starts_at": selectable[0]["starts_at"],
                "ends_at": selectable[0]["ends_at"],
            }
        items.append(
            {
                "id": computer.pk,
                "code": computer.code,
                "description": computer.description,
                "operational_state": computer.operational_state,
                "effective_status_now": status_now,
                "can_start_now": can_start_now,
                "available_slot_count": len(selectable),
                "next_available_slot": next_slot,
            }
        )

    return (
        {
            "date": target_date,
            "is_today": is_today,
            "slot_duration_minutes": duration,
            "generated_at": current,
            "computers": items,
        },
        slots_by_computer,
    )


def get_computer_slots(
    *,
    target_date: date,
    computer: Computer,
    user_reference: str | None,
    now=None,
):
    summary, slots_by_computer = get_computers_availability(
        target_date=target_date,
        computers=[computer],
        user_reference=user_reference,
        now=now,
    )
    return {
        "computer": computer,
        "date": summary["date"],
        "is_today": summary["is_today"],
        "slot_duration_minutes": summary["slot_duration_minutes"],
        "slots": slots_by_computer[computer.pk],
    }
