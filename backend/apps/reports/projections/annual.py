from .common import (
    NOT_INFORMED,
    build_occupancy,
    build_summary,
    month_bounds,
    segments_minutes,
    shift_columns,
    standard_warnings,
    visits_by_shift,
    year_bounds,
)


def _inside(value, starts_at, ends_at):
    return starts_at <= value < ends_at


def build_annual_report(
    *,
    year,
    sessions,
    allocations,
    reservations,
    occurrences,
    shifts,
    operating_days,
    computers,
    now,
):
    period_start, period_end = year_bounds(year)
    sessions = list(sessions)
    allocations = list(allocations)
    reservations = list(reservations)
    occurrences = list(occurrences)
    operating_days = list(operating_days)
    computers = list(computers)
    columns = shift_columns(shifts, sessions)
    column_keys = [item["series_key"] for item in columns] + [NOT_INFORMED]

    occupancy, excluded = build_occupancy(
        period_start=period_start,
        period_end=period_end,
        now=now,
        operating_days=operating_days,
        computers=computers,
        allocations=allocations,
    )

    months = []
    for month in range(1, 13):
        month_start, month_end = month_bounds(year, month)
        month_sessions = [
            session
            for session in sessions
            if _inside(session.started_at, month_start, month_end)
        ]
        month_allocations = [
            allocation
            for allocation in allocations
            if allocation.started_at < month_end
            and (allocation.ended_at is None or allocation.ended_at > month_start)
        ]
        month_reservations = [
            reservation
            for reservation in reservations
            if _inside(reservation.starts_at, month_start, month_end)
        ]
        month_occurrences = [
            occurrence
            for occurrence in occurrences
            if _inside(occurrence.created_at, month_start, month_end)
        ]
        month_operating_days = [
            item
            for item in operating_days
            if item.date.year == year and item.date.month == month
        ]
        month_available = segments_minutes(
            occupancy.available_segments,
            month_start,
            month_end,
        )
        month_allocated = segments_minutes(
            occupancy.allocated_segments,
            month_start,
            month_end,
        )
        calculated_until = min(month_end, now)
        if calculated_until < month_start:
            calculated_until = month_start
        existing_computers = [
            computer for computer in computers if computer.created_at < calculated_until
        ]
        excluded_in_month = [
            computer for computer in existing_computers if computer.code in excluded
        ]
        month_summary = build_summary(
            period_start=month_start,
            period_end=month_end,
            sessions=month_sessions,
            allocations=month_allocations,
            reservations=month_reservations,
            occurrences=month_occurrences,
            operating_days=month_operating_days,
            now=now,
        )
        month_visits = visits_by_shift(month_sessions, column_keys)
        months.append(
            {
                "month": month,
                "visits_by_shift": month_visits,
                "total": len(month_sessions),
                "summary": month_summary,
                "occupancy": {
                    "allocated_minutes": month_allocated,
                    "available_minutes": month_available,
                    "rate_percent": (
                        round(month_allocated * 100 / month_available, 2)
                        if month_available
                        else None
                    ),
                    "computers_considered": (
                        len(existing_computers) - len(excluded_in_month)
                    ),
                    "computers_excluded": len(excluded_in_month),
                    "calculated_until": calculated_until.isoformat(),
                },
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
    return {
        "period": {
            "year": year,
            "starts_at": period_start.isoformat(),
            "ends_at": period_end.isoformat(),
        },
        "shifts": columns,
        "months": months,
        "totals_by_shift": {
            key: sum(month["visits_by_shift"].get(key, 0) for month in months)
            for key in column_keys
        },
        "summary": summary,
        "occupancy": occupancy.payload,
        "warnings": standard_warnings(sessions, excluded),
    }
