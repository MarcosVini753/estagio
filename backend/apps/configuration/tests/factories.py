from datetime import date, time

from apps.configuration.models import (
    OperatingSchedule,
    OperatingScheduleDay,
    OperatingWindow,
    Weekday,
)


def create_operating_schedule(
    *,
    schedule_type=OperatingSchedule.ScheduleType.REGULAR,
    valid_from=date(2025, 1, 1),
    valid_until=None,
    weekday_windows=None,
    name="Horário de teste",
):
    weekday_windows = weekday_windows or {
        weekday: [(time(7, 15), time(21))] for weekday in range(5)
    } | {Weekday.SATURDAY: [(time(7, 15), time(13))]}
    schedule = OperatingSchedule.objects.create(
        name=name,
        schedule_type=schedule_type,
        valid_from=valid_from,
        valid_until=valid_until,
        created_by_profile="LIBRARY_SUPERVISOR",
    )
    for weekday in Weekday.values:
        windows = weekday_windows.get(weekday, [])
        day = OperatingScheduleDay.objects.create(
            schedule=schedule,
            weekday=weekday,
            is_open=bool(windows),
        )
        for display_order, (opens_at, closes_at) in enumerate(windows):
            OperatingWindow.objects.create(
                schedule_day=day,
                opens_at=opens_at,
                closes_at=closes_at,
                display_order=display_order,
            )
    return schedule
