from apps.configuration.calendar import operating_minutes

from .common import (
    NOT_INFORMED,
    build_occupancy,
    build_summary,
    date_bounds,
    shift_columns,
    standard_warnings,
    visits_by_shift,
)


def build_daily_report(
    *,
    target_date,
    sessions,
    allocations,
    reservations,
    occurrences,
    shifts,
    operating_days,
    computers,
    now,
):
    period_start, period_end = date_bounds(target_date)
    sessions = list(sessions)
    allocations = list(allocations)
    reservations = list(reservations)
    occurrences = list(occurrences)
    operating_days = list(operating_days)
    operating_day = operating_days[0]
    columns = shift_columns(shifts, sessions)
    column_keys = [item["series_key"] for item in columns] + [NOT_INFORMED]
    shift_visits = visits_by_shift(sessions, column_keys)
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
            "date": target_date.isoformat(),
            "starts_at": period_start.isoformat(),
            "ends_at": period_end.isoformat(),
        },
        "calendar": {
            "status": operating_day.status,
            "source": operating_day.source,
            "reason": operating_day.reason,
            "windows": [
                {
                    "opens_at": window.opens_at.isoformat(timespec="minutes"),
                    "closes_at": window.closes_at.isoformat(timespec="minutes"),
                }
                for window in operating_day.windows
            ],
            "operating_minutes": operating_minutes(operating_day),
        },
        "shifts": columns,
        "visits_by_shift": shift_visits,
        "total": len(sessions),
        "summary": summary,
        "occupancy": occupancy.payload,
        "warnings": standard_warnings(sessions, excluded),
    }
