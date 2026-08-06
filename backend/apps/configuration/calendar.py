from dataclasses import dataclass
from datetime import date, datetime, time

from django.db import connection
from django.utils import timezone

from apps.core.api.errors import (
    OperatingDayConfigurationInvalid,
    OperatingScheduleRequired,
)

from .models import CalendarException, OperatingSchedule, Weekday
from .selectors import (
    get_active_room_notices,
    get_calendar_exception_for_date,
    get_effective_operating_schedule_for_date,
)


class RoomStatus:
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    SPECIAL_HOURS = "SPECIAL_HOURS"


class CalendarSource:
    CALENDAR_EXCEPTION = "CALENDAR_EXCEPTION"
    TEMPORARY_SCHEDULE = "TEMPORARY_SCHEDULE"
    REGULAR_SCHEDULE = "REGULAR_SCHEDULE"


ROOM_STATUS_CHOICES = [
    RoomStatus.OPEN,
    RoomStatus.CLOSED,
    RoomStatus.SPECIAL_HOURS,
]
CALENDAR_SOURCE_CHOICES = [
    CalendarSource.CALENDAR_EXCEPTION,
    CalendarSource.TEMPORARY_SCHEDULE,
    CalendarSource.REGULAR_SCHEDULE,
]


def lock_operating_date(target_date: date) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_advisory_xact_lock(hashtext(%s))",
            [f"operating-calendar:{target_date.isoformat()}"],
        )


@dataclass(frozen=True)
class OperatingWindowResult:
    opens_at: time
    closes_at: time


@dataclass(frozen=True)
class OperatingDayResult:
    date: date
    status: str
    source: str
    windows: tuple[OperatingWindowResult, ...]
    reason: str = ""
    schedule_id: int | None = None
    exception_id: int | None = None

    @property
    def is_closed(self) -> bool:
        return self.status == RoomStatus.CLOSED


def aware_at(target_date: date, target_time: time) -> datetime:
    value = datetime.combine(target_date, target_time)
    return timezone.make_aware(value, timezone.get_current_timezone())


def as_datetime_windows(
    operating_day: OperatingDayResult,
) -> list[tuple[datetime, datetime]]:
    return [
        (
            aware_at(operating_day.date, window.opens_at),
            aware_at(operating_day.date, window.closes_at),
        )
        for window in operating_day.windows
    ]


def is_open_at(operating_day: OperatingDayResult, instant: datetime) -> bool:
    if operating_day.is_closed:
        return False
    return any(
        starts_at <= instant < ends_at
        for starts_at, ends_at in as_datetime_windows(operating_day)
    )


def interval_is_within_operating_day(
    operating_day: OperatingDayResult,
    starts_at: datetime,
    ends_at: datetime,
) -> bool:
    return any(
        window_start <= starts_at and ends_at <= window_end
        for window_start, window_end in as_datetime_windows(operating_day)
    )


def operating_minutes(operating_day: OperatingDayResult) -> int:
    return sum(
        int(
            (
                datetime.combine(operating_day.date, window.closes_at)
                - datetime.combine(operating_day.date, window.opens_at)
            ).total_seconds()
            // 60
        )
        for window in operating_day.windows
    )


def room_notice_payload(notice) -> dict:
    return {
        "id": notice.pk,
        "notice_type": notice.notice_type,
        "title": notice.title,
        "message": notice.message,
        "effective_from": notice.effective_from,
        "effective_until": notice.effective_until,
        "visible_from": notice.visible_from,
        "visible_until": notice.visible_until,
        "is_active": notice.is_active,
        "created_by_profile": notice.created_by_profile,
        "operating_schedule_id": notice.operating_schedule_id,
        "calendar_exception_id": notice.calendar_exception_id,
        "created_at": notice.created_at,
        "updated_at": notice.updated_at,
    }


def room_status_payload(
    target_date: date,
    *,
    now: datetime | None = None,
    operating_day: OperatingDayResult | None = None,
) -> dict:
    current = now or timezone.now()
    operating_day = operating_day or resolve_operating_day(target_date)
    return {
        "date": target_date,
        "status": operating_day.status,
        "source": operating_day.source,
        "is_open_now": (
            target_date == timezone.localdate(current)
            and is_open_at(operating_day, current)
        ),
        "reason": operating_day.reason,
        "operating_windows": [
            {
                "opens_at": window.opens_at.isoformat(),
                "closes_at": window.closes_at.isoformat(),
            }
            for window in operating_day.windows
        ],
        "active_notices": [
            room_notice_payload(notice)
            for notice in get_active_room_notices(
                at=current,
                target_date=target_date,
            )
        ],
    }


def _closed_reason(target_date: date) -> str:
    if target_date.weekday() == Weekday.SUNDAY:
        return "A Sala de Informática não funciona aos domingos."
    return "A Sala de Informática não funciona nesta data."


def _from_exception(
    target_date: date,
    exception: CalendarException,
) -> OperatingDayResult:
    if exception.exception_type == CalendarException.ExceptionType.SPECIAL_HOURS:
        if not exception.opens_at or not exception.closes_at:
            raise OperatingDayConfigurationInvalid(
                "A exceção de horário especial não possui uma janela válida."
            )
        windows = (OperatingWindowResult(exception.opens_at, exception.closes_at),)
        status = RoomStatus.SPECIAL_HOURS
    else:
        windows = ()
        status = RoomStatus.CLOSED
    return OperatingDayResult(
        date=target_date,
        status=status,
        source=CalendarSource.CALENDAR_EXCEPTION,
        windows=windows,
        reason=exception.description
        or (
            "A Sala de Informática está fechada nesta data."
            if status == RoomStatus.CLOSED
            else "Horário especial nesta data."
        ),
        exception_id=exception.pk,
    )


def resolve_operating_day(target_date: date) -> OperatingDayResult:
    exception = get_calendar_exception_for_date(target_date)
    if exception is not None:
        return _from_exception(target_date, exception)

    schedule = get_effective_operating_schedule_for_date(target_date)
    if schedule is None:
        raise OperatingScheduleRequired()
    days = [day for day in schedule.days.all() if day.weekday == target_date.weekday()]
    if len(days) != 1:
        raise OperatingDayConfigurationInvalid(
            "O calendário aplicável não possui exatamente um registro para este dia."
        )
    day = days[0]
    windows = tuple(
        OperatingWindowResult(window.opens_at, window.closes_at)
        for window in day.windows.all()
    )
    if day.is_open and not windows:
        raise OperatingDayConfigurationInvalid(
            "Dia aberto sem janela de funcionamento."
        )
    if not day.is_open and windows:
        raise OperatingDayConfigurationInvalid(
            "Dia fechado com janela de funcionamento."
        )

    source = (
        CalendarSource.TEMPORARY_SCHEDULE
        if schedule.schedule_type == OperatingSchedule.ScheduleType.TEMPORARY
        else CalendarSource.REGULAR_SCHEDULE
    )
    return OperatingDayResult(
        date=target_date,
        status=(
            RoomStatus.CLOSED
            if not day.is_open
            else (
                RoomStatus.SPECIAL_HOURS
                if schedule.schedule_type == OperatingSchedule.ScheduleType.TEMPORARY
                else RoomStatus.OPEN
            )
        ),
        source=source,
        windows=windows,
        reason="" if day.is_open else _closed_reason(target_date),
        schedule_id=schedule.pk,
    )
