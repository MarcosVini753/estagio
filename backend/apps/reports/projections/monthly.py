from calendar import monthrange
from datetime import date

from django.utils import timezone

from apps.configuration.calendar import operating_minutes

from .common import (
    NOT_INFORMED,
    REPORT_TIME_ZONE,
    build_occupancy,
    build_summary,
    month_bounds,
    shift_columns,
    standard_warnings,
    visits_by_shift,
)


def build_monthly_report(
    *,
    year,
    month,
    sessions,
    allocations,
    reservations,
    occurrences,
    shifts,
    operating_days,
    computers=(),
    now=None,
):
    period_start, period_end = month_bounds(year, month)
    now = now or timezone.now()
    sessions = list(sessions)
    allocations = list(allocations)
    reservations = list(reservations)
    occurrences = list(occurrences)
    operating_days = list(operating_days)
    columns = shift_columns(shifts, sessions)
    column_keys = [item["series_key"] for item in columns] + [NOT_INFORMED]
    operating_days_by_date = {item.date: item for item in operating_days}

    days = []
    for day_number in range(1, monthrange(year, month)[1] + 1):
        current_date = date(year, month, day_number)
        operating_day = operating_days_by_date[current_date]
        day_sessions = [
            session
            for session in sessions
            if timezone.localtime(session.started_at, REPORT_TIME_ZONE).date()
            == current_date
        ]
        day_visits = visits_by_shift(day_sessions, column_keys)
        days.append(
            {
                "date": current_date.isoformat(),
                "day": day_number,
                "calendar_status": operating_day.status,
                "calendar_source": operating_day.source,
                "operating_minutes": operating_minutes(operating_day),
                "visits_by_shift": day_visits,
                "total": len(day_sessions),
            }
        )

    summary = build_summary(
        period_start=period_start,
        period_end=period_end,
        sessions=sessions,
        allocations=allocations,
        reservations=reservations,
        occurrences=occurrences,
        operating_days=operating_days,
        now=now,
    )
    occupancy, excluded = build_occupancy(
        period_start=period_start,
        period_end=period_end,
        now=now,
        operating_days=operating_days,
        computers=list(computers),
        allocations=allocations,
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
        "totals_by_shift": {
            key: sum(day["visits_by_shift"].get(key, 0) for day in days)
            for key in column_keys
        },
        "summary": summary,
        "occupancy": occupancy.payload,
        "warnings": standard_warnings(sessions, excluded),
    }
