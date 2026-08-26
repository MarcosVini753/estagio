from collections import defaultdict
from datetime import date, datetime, time, timedelta

from django.db.models import Q
from django.utils import timezone

from apps.computers.models import Computer
from apps.configuration.calendar import (
    OperatingDayResult,
    as_datetime_windows,
    aware_at,
    resolve_operating_day,
    room_status_payload,
)
from apps.core.api.errors import DateOutsideAllowedWindow
from apps.operations.models import ComputerAllocation, Reservation, UseSession
from apps.operations.rules import SLOT_DURATION_MINUTES
from apps.operations.slotting import (
    ACTIVE_ALLOCATION,
    COMPUTER_UNAVAILABLE,
    NEXT_RESERVATION,
    USER_RESERVATION,
    immediate_planned_end_options,
)

OCCUPIED = "OCCUPIED"
RESERVED = "RESERVED"
BLOCKING_RESERVATION_STATUSES = [Reservation.Status.CONFIRMED]


def validate_target_date(target_date: date, *, now=None) -> date:
    current = now or timezone.now()
    today = timezone.localdate(current)
    if target_date not in {today, today + timedelta(days=1)}:
        raise DateOutsideAllowedWindow()
    return today


def generate_slot_intervals(
    target_date: date,
    *,
    operating_day: OperatingDayResult | None = None,
) -> tuple[int, list[tuple[datetime, datetime]], list[tuple[datetime, datetime]]]:
    operating_day = operating_day or resolve_operating_day(target_date)
    windows = as_datetime_windows(operating_day)
    duration = timedelta(minutes=SLOT_DURATION_MINUTES)
    slots = []
    for window_start, window_end in windows:
        cursor = window_start
        while cursor + duration <= window_end:
            slots.append((cursor, cursor + duration))
            cursor += duration
    return SLOT_DURATION_MINUTES, windows, slots


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

    day_start = aware_at(target_date, time.min)
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
        .select_related("session")
        .only(
            "computer_id",
            "started_at",
            "ended_at",
            "session__planned_ends_at",
            "session__exit_deadline_at",
        )
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
    *,
    current_status: bool = False,
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
            (
                allocation.ended_at
                or (
                    allocation.session.exit_deadline_at
                    if current_status
                    else allocation.session.planned_ends_at
                )
            ),
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


def _immediate_usage_payload(
    *,
    computer: Computer,
    current: datetime,
    operating_day: OperatingDayResult,
    allocations,
    reservations,
    user_reservations,
    user_has_active_allocation: bool,
    include_planned_end_options: bool = False,
) -> dict:
    def unavailable(limited_by):
        payload = {
            "can_start_now": False,
            "max_planned_ends_at": None,
            "limited_by": limited_by,
        }
        if include_planned_end_options:
            payload["planned_end_options"] = []
        return payload

    if computer.operational_state != Computer.OperationalState.AVAILABLE:
        return unavailable(COMPUTER_UNAVAILABLE)

    if any(
        _overlaps(
            current,
            current + timedelta(microseconds=1),
            allocation.started_at,
            allocation.ended_at or allocation.session.exit_deadline_at,
        )
        for allocation in allocations
    ):
        return unavailable(ACTIVE_ALLOCATION)

    if user_has_active_allocation:
        return unavailable(ACTIVE_ALLOCATION)

    limits = [
        (reservation.starts_at, NEXT_RESERVATION)
        for reservation in reservations
        if reservation.ends_at > current
    ]
    limits.extend(
        (reservation.starts_at, USER_RESERVATION)
        for reservation in user_reservations
        if reservation.ends_at > current
    )
    planned_end_options, limited_by = immediate_planned_end_options(
        starts_at=current,
        operating_day=operating_day,
        limits=limits,
    )
    payload = {
        "can_start_now": bool(planned_end_options),
        "max_planned_ends_at": (
            planned_end_options[-1] if planned_end_options else None
        ),
        "limited_by": limited_by,
    }
    if include_planned_end_options:
        payload["planned_end_options"] = planned_end_options
    return payload


def get_computers_availability(
    *,
    target_date: date,
    computers,
    user_reference: str | None,
    now=None,
    include_planned_end_options: bool = False,
):
    current = now or timezone.now()
    today = validate_target_date(target_date, now=current)
    is_today = target_date == today
    operating_day = resolve_operating_day(target_date)
    duration, windows, intervals = generate_slot_intervals(
        target_date,
        operating_day=operating_day,
    )
    computer_list = list(computers)
    allocations, reservations = _load_events(
        computer_list,
        target_date,
        windows,
        now=current,
    )
    user_reservations = (
        list(
            Reservation.objects.filter(
                user_reference=user_reference,
                status=Reservation.Status.CONFIRMED,
                starts_at__lt=(aware_at(target_date, time.min) + timedelta(days=1)),
                ends_at__gt=current,
            ).only("starts_at", "ends_at")
        )
        if is_today and user_reference
        else []
    )
    user_has_active_allocation = bool(
        is_today
        and user_reference
        and UseSession.objects.filter(
            user_reference=user_reference,
            status=UseSession.Status.ACTIVE,
            exit_deadline_at__gt=current,
            allocations__ended_at__isnull=True,
        ).exists()
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
        immediate_usage = {
            "can_start_now": False,
            "max_planned_ends_at": None,
            "limited_by": None,
        }
        if include_planned_end_options:
            immediate_usage["planned_end_options"] = []
        if is_today:
            status_now = _effective_status(
                computer,
                current,
                current + timedelta(microseconds=1),
                computer_allocations,
                computer_reservations,
                current_status=True,
            )
            immediate_usage = _immediate_usage_payload(
                computer=computer,
                current=current,
                operating_day=operating_day,
                allocations=computer_allocations,
                reservations=computer_reservations,
                user_reservations=user_reservations,
                user_has_active_allocation=user_has_active_allocation,
                include_planned_end_options=include_planned_end_options,
            )
            can_start_now = immediate_usage["can_start_now"]

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
                "immediate_usage": immediate_usage,
                "available_slot_count": len(selectable),
                "next_available_slot": next_slot,
            }
        )

    room = room_status_payload(
        target_date,
        now=current,
        operating_day=operating_day,
    )
    room.pop("date")
    room.pop("is_open_now")
    return (
        {
            "date": target_date,
            "is_today": is_today,
            "slot_duration_minutes": duration,
            "generated_at": current,
            "room": room,
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
        include_planned_end_options=True,
    )
    return {
        "computer": computer,
        "date": summary["date"],
        "is_today": summary["is_today"],
        "slot_duration_minutes": summary["slot_duration_minutes"],
        "immediate_usage": summary["computers"][0]["immediate_usage"],
        "room": summary["room"],
        "slots": slots_by_computer[computer.pk],
    }
