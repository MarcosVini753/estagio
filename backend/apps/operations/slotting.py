from collections.abc import Iterable
from datetime import datetime, time, timedelta

from django.utils import timezone

from apps.configuration.calendar import (
    OperatingDayResult,
    as_datetime_windows,
    aware_at,
    interval_is_within_operating_day,
)

from .rules import SLOT_DURATION_MINUTES

NEXT_RESERVATION = "NEXT_RESERVATION"
USER_RESERVATION = "USER_RESERVATION"
ROOM_CLOSING = "ROOM_CLOSING"
ACTIVE_ALLOCATION = "ACTIVE_ALLOCATION"
COMPUTER_UNAVAILABLE = "COMPUTER_UNAVAILABLE"

IMMEDIATE_USAGE_LIMIT_CHOICES = [
    NEXT_RESERVATION,
    USER_RESERVATION,
    ROOM_CLOSING,
    ACTIVE_ALLOCATION,
    COMPUTER_UNAVAILABLE,
]

_LIMIT_PRIORITY = {
    USER_RESERVATION: 0,
    NEXT_RESERVATION: 1,
    ROOM_CLOSING: 2,
}


def calculate_interval(starts_at: datetime, slot_count: int) -> datetime:
    if (
        isinstance(slot_count, bool)
        or not isinstance(slot_count, int)
        or slot_count < 1
    ):
        raise ValueError("slot_count deve ser um inteiro positivo.")
    try:
        return starts_at + timedelta(minutes=slot_count * SLOT_DURATION_MINUTES)
    except OverflowError as error:
        raise ValueError("slot_count excede o intervalo temporal suportado.") from error


def validate_reservation_slot_start(
    starts_at: datetime,
    operating_day: OperatingDayResult,
) -> None:
    duration = timedelta(minutes=SLOT_DURATION_MINUTES)
    for window_start, window_end in as_datetime_windows(operating_day):
        if window_start <= starts_at < window_end:
            if (starts_at - window_start) % duration == timedelta(0):
                return
            break
    raise ValueError("O início deve estar alinhado à grade de 15 minutos.")


def validate_interval_inside_operating_window(
    starts_at: datetime,
    ends_at: datetime,
    operating_day: OperatingDayResult,
) -> None:
    if starts_at >= ends_at or not interval_is_within_operating_day(
        operating_day,
        starts_at,
        ends_at,
    ):
        raise ValueError("O intervalo deve caber em uma janela de funcionamento.")


def immediate_planned_end_options(
    *,
    starts_at: datetime,
    operating_day: OperatingDayResult,
    limits: Iterable[tuple[datetime, str]] = (),
) -> tuple[list[datetime], str]:
    containing_window = next(
        (
            (window_start, window_end)
            for window_start, window_end in as_datetime_windows(operating_day)
            if window_start <= starts_at < window_end
        ),
        None,
    )
    if containing_window is None:
        return [], ROOM_CLOSING

    candidates = [(containing_window[1], ROOM_CLOSING), *limits]
    limit_at, limited_by = min(
        candidates,
        key=lambda item: (item[0], _LIMIT_PRIORITY.get(item[1], 99)),
    )
    duration = timedelta(minutes=SLOT_DURATION_MINUTES)
    anchor = aware_at(timezone.localdate(starts_at), time(7, 15))
    first_end = anchor + ((starts_at - anchor) // duration + 1) * duration
    options = []
    candidate = first_end
    while candidate <= limit_at:
        options.append(candidate)
        candidate += duration
    return options, limited_by


def validate_immediate_planned_end(
    *,
    starts_at: datetime,
    planned_ends_at: datetime,
    operating_day: OperatingDayResult,
) -> None:
    duration = timedelta(minutes=SLOT_DURATION_MINUTES)
    anchor = aware_at(timezone.localdate(starts_at), time(7, 15))
    if planned_ends_at <= starts_at or (
        planned_ends_at - anchor
    ) % duration != timedelta(0):
        raise ValueError("O fim deve estar na grade de 15 minutos posterior à entrada.")
    validate_interval_inside_operating_window(
        starts_at,
        planned_ends_at,
        operating_day,
    )
