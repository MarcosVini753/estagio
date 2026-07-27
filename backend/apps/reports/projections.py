from calendar import monthrange
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from django.utils import timezone

from apps.operations.models import UseSession

REPORT_TIME_ZONE = ZoneInfo("America/Rio_Branco")
NOT_INFORMED = "NOT_INFORMED"


def month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    starts_on = date(year, month, 1)
    ends_on = date(year + (month == 12), month % 12 + 1, 1)
    return (
        timezone.make_aware(datetime.combine(starts_on, time.min), REPORT_TIME_ZONE),
        timezone.make_aware(datetime.combine(ends_on, time.min), REPORT_TIME_ZONE),
    )


def overlap_minutes(
    started_at: datetime,
    ended_at: datetime | None,
    window_starts_at: datetime,
    window_ends_at: datetime,
    *,
    now: datetime,
) -> int:
    effective_end = ended_at or min(now, window_ends_at)
    overlap_start = max(started_at, window_starts_at)
    overlap_end = min(effective_end, window_ends_at)
    if overlap_end <= overlap_start:
        return 0
    return int((overlap_end - overlap_start).total_seconds() // 60)


def build_monthly_report(
    *,
    year,
    month,
    sessions,
    allocations,
    reservations,
    occurrences,
    shifts,
    calendar_exceptions,
    now=None,
):
    period_start, period_end = month_bounds(year, month)
    now = now or timezone.now()
    sessions = list(sessions)
    allocations = list(allocations)

    shift_columns = {}
    for shift in shifts:
        shift_columns[str(shift.series_key)] = {
            "series_key": str(shift.series_key),
            "name": shift.name,
            "display_order": shift.display_order,
        }
    for session in sessions:
        if session.start_shift:
            shift = session.start_shift
            shift_columns.setdefault(
                str(shift.series_key),
                {
                    "series_key": str(shift.series_key),
                    "name": shift.name,
                    "display_order": shift.display_order,
                },
            )
    columns = sorted(
        shift_columns.values(),
        key=lambda item: (item["display_order"], item["name"]),
    )
    column_keys = [item["series_key"] for item in columns] + [NOT_INFORMED]

    exceptions = {item.date: item.exception_type for item in calendar_exceptions}
    days = []
    day_rows = {}
    for day_number in range(1, monthrange(year, month)[1] + 1):
        current_date = date(year, month, day_number)
        row = {
            "date": current_date.isoformat(),
            "day": day_number,
            "calendar_status": exceptions.get(current_date, "OPEN"),
            "visits_by_shift": dict.fromkeys(column_keys, 0),
            "total": 0,
        }
        days.append(row)
        day_rows[current_date] = row

    active_session_ids = []
    sessions_without_shift = []
    finished_durations = []
    for session in sessions:
        local_date = timezone.localtime(session.started_at, REPORT_TIME_ZONE).date()
        column_key = (
            str(session.start_shift.series_key) if session.start_shift else NOT_INFORMED
        )
        row = day_rows[local_date]
        row["visits_by_shift"][column_key] += 1
        row["total"] += 1
        if session.status == UseSession.Status.ACTIVE:
            active_session_ids.append(session.pk)
        elif (
            session.status == UseSession.Status.FINISHED
            and session.ended_at
            and session.ended_at >= session.started_at
        ):
            finished_durations.append(session.ended_at - session.started_at)
        if not session.start_shift:
            sessions_without_shift.append(session.pk)

    totals_by_shift = {
        key: sum(row["visits_by_shift"][key] for row in days) for key in column_keys
    }
    allocated_minutes = sum(
        overlap_minutes(
            allocation.started_at,
            allocation.ended_at,
            period_start,
            period_end,
            now=now,
        )
        for allocation in allocations
    )
    average_stay_minutes = (
        round(
            sum(duration.total_seconds() for duration in finished_durations)
            / len(finished_durations)
            / 60
        )
        if finished_durations
        else 0
    )

    return {
        "period": {
            "year": year,
            "month": month,
            "starts_at": period_start.isoformat(),
            "ends_at": period_end.isoformat(),
        },
        "shifts": columns,
        "days": days,
        "totals_by_shift": totals_by_shift,
        "summary": {
            "visits": len(sessions),
            "distinct_users": len({session.user_reference for session in sessions}),
            "reservations": len(reservations),
            "occurrences": len(occurrences),
            "computers_used": len(
                {allocation.computer_id for allocation in allocations}
            ),
            "allocated_minutes": allocated_minutes,
            "average_stay_minutes": average_stay_minutes,
        },
        "warnings": {
            "active_session_ids": active_session_ids,
            "sessions_without_shift": sessions_without_shift,
        },
    }
