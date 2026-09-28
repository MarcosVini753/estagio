from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone

from apps.computers.models import Computer
from apps.configuration.calendar import as_datetime_windows, operating_minutes
from apps.core.enums import AffiliationType
from apps.operations.models import Reservation, UseSession

REPORT_TIME_ZONE = ZoneInfo("America/Rio_Branco")
NOT_INFORMED = "NOT_INFORMED"


def date_bounds(target_date: date) -> tuple[datetime, datetime]:
    starts_at = timezone.make_aware(
        datetime.combine(target_date, time.min),
        REPORT_TIME_ZONE,
    )
    return starts_at, starts_at + timedelta(days=1)


def month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    starts_on = date(year, month, 1)
    ends_on = date(year + (month == 12), month % 12 + 1, 1)
    return date_bounds(starts_on)[0], date_bounds(ends_on)[0]


def year_bounds(year: int) -> tuple[datetime, datetime]:
    return date_bounds(date(year, 1, 1))[0], date_bounds(date(year + 1, 1, 1))[0]


def inclusive_period_bounds(
    starts_on: date,
    ends_on: date,
) -> tuple[datetime, datetime]:
    return date_bounds(starts_on)[0], date_bounds(ends_on + timedelta(days=1))[0]


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


def _intersection(
    first_start: datetime,
    first_end: datetime,
    second_start: datetime,
    second_end: datetime,
) -> tuple[datetime, datetime] | None:
    starts_at = max(first_start, second_start)
    ends_at = min(first_end, second_end)
    return (starts_at, ends_at) if starts_at < ends_at else None


def interval_minutes(starts_at: datetime, ends_at: datetime) -> int:
    return max(0, int((ends_at - starts_at).total_seconds() // 60))


def shift_columns(shifts, sessions=()):
    values = {}
    for shift in shifts:
        values[str(shift.series_key)] = {
            "series_key": str(shift.series_key),
            "name": shift.name,
            "display_order": shift.display_order,
        }
    for session in sessions:
        if session.start_shift:
            shift = session.start_shift
            values.setdefault(
                str(shift.series_key),
                {
                    "series_key": str(shift.series_key),
                    "name": shift.name,
                    "display_order": shift.display_order,
                },
            )
    return sorted(
        values.values(),
        key=lambda item: (item["display_order"], item["name"]),
    )


def visits_by_shift(sessions, column_keys):
    totals = dict.fromkeys(column_keys, 0)
    for session in sessions:
        key = (
            str(session.start_shift.series_key) if session.start_shift else NOT_INFORMED
        )
        totals.setdefault(key, 0)
        totals[key] += 1
    return totals


def build_summary(
    *,
    period_start,
    period_end,
    sessions,
    allocations,
    reservations,
    occurrences,
    operating_days,
    now,
):
    sessions = list(sessions)
    allocations = list(allocations)
    reservations = list(reservations)
    finished_durations = [
        session.ended_at - session.started_at
        for session in sessions
        if session.status == UseSession.Status.FINISHED
        and session.ended_at
        and session.ended_at >= session.started_at
    ]
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
        "visits": len(sessions),
        "distinct_users": len({session.user_reference for session in sessions}),
        "reservations": len(reservations),
        "reservations_by_status": {
            status: sum(item.status == status for item in reservations)
            for status in Reservation.Status.values
        },
        "occurrences": len(occurrences),
        "computers_used": len({allocation.computer_id for allocation in allocations}),
        "allocated_minutes": sum(
            overlap_minutes(
                allocation.started_at,
                allocation.ended_at,
                period_start,
                period_end,
                now=now,
            )
            for allocation in allocations
        ),
        "average_stay_minutes": average_stay_minutes,
        "operating_minutes": sum(
            operating_minutes(operating_day) for operating_day in operating_days
        ),
    }


@dataclass(frozen=True)
class OccupancyProjection:
    payload: dict
    computers: list[dict]
    available_segments: list[tuple[int, datetime, datetime]]
    allocated_segments: list[tuple[int, datetime, datetime]]


def _state_intervals(computer, *, effective_end):
    created_at = computer.created_at
    changes = sorted(
        getattr(computer, "report_state_changes", ()),
        key=lambda item: (item.changed_at, item.pk),
    )
    if created_at >= effective_end:
        return [], True
    if not changes:
        return [(created_at, effective_end, computer.operational_state)], True

    state = changes[0].previous_state
    cursor = created_at
    intervals = []
    reliable = changes[0].changed_at >= created_at
    for change in changes:
        if change.previous_state != state or change.changed_at < cursor:
            reliable = False
            break
        if cursor < change.changed_at:
            intervals.append((cursor, change.changed_at, state))
        cursor = change.changed_at
        state = change.new_state
    if state != computer.operational_state:
        reliable = False
    if cursor < effective_end:
        intervals.append((cursor, effective_end, state))
    return intervals, reliable


def build_occupancy(
    *,
    period_start,
    period_end,
    now,
    operating_days,
    computers,
    allocations,
):
    effective_end = min(period_end, now)
    if effective_end <= period_start:
        effective_end = period_start
    calendar_windows = []
    for operating_day in operating_days:
        for starts_at, ends_at in as_datetime_windows(operating_day):
            clipped = _intersection(
                starts_at,
                ends_at,
                period_start,
                effective_end,
            )
            if clipped:
                calendar_windows.append(clipped)

    allocations_by_computer = defaultdict(list)
    for allocation in allocations:
        allocations_by_computer[allocation.computer_id].append(allocation)

    available_segments = []
    allocated_segments = []
    computer_rows = []
    excluded = []
    considered = 0
    for computer in computers:
        if computer.created_at >= effective_end:
            continue
        intervals, reliable = _state_intervals(
            computer,
            effective_end=effective_end,
        )
        if not reliable:
            excluded.append(computer.code)
            continue
        considered += 1
        computer_available = []
        for state_start, state_end, state in intervals:
            if state != Computer.OperationalState.AVAILABLE:
                continue
            for window_start, window_end in calendar_windows:
                clipped = _intersection(
                    state_start,
                    state_end,
                    window_start,
                    window_end,
                )
                if clipped:
                    segment = (computer.pk, *clipped)
                    available_segments.append(segment)
                    computer_available.append(segment)

        computer_allocated = []
        for allocation in allocations_by_computer[computer.pk]:
            allocation_end = allocation.ended_at or effective_end
            for _, available_start, available_end in computer_available:
                clipped = _intersection(
                    allocation.started_at,
                    allocation_end,
                    available_start,
                    available_end,
                )
                if clipped:
                    segment = (computer.pk, *clipped)
                    allocated_segments.append(segment)
                    computer_allocated.append(segment)

        available_minutes = sum(
            interval_minutes(starts_at, ends_at)
            for _, starts_at, ends_at in computer_available
        )
        allocated_minutes = sum(
            interval_minutes(starts_at, ends_at)
            for _, starts_at, ends_at in computer_allocated
        )
        computer_rows.append(
            {
                "computer_id": computer.pk,
                "code": computer.code,
                "description": computer.description,
                "available_minutes": available_minutes,
                "allocated_minutes": allocated_minutes,
                "occupancy_rate_percent": (
                    round(allocated_minutes * 100 / available_minutes, 2)
                    if available_minutes
                    else None
                ),
            }
        )

    available_minutes = sum(
        interval_minutes(starts_at, ends_at)
        for _, starts_at, ends_at in available_segments
    )
    allocated_minutes = sum(
        interval_minutes(starts_at, ends_at)
        for _, starts_at, ends_at in allocated_segments
    )
    return OccupancyProjection(
        payload={
            "allocated_minutes": allocated_minutes,
            "available_minutes": available_minutes,
            "rate_percent": (
                round(allocated_minutes * 100 / available_minutes, 2)
                if available_minutes
                else None
            ),
            "computers_considered": considered,
            "computers_excluded": len(excluded),
            "calculated_until": effective_end.isoformat(),
        },
        computers=computer_rows,
        available_segments=available_segments,
        allocated_segments=allocated_segments,
    ), excluded


def standard_warnings(sessions, excluded_computers=()):
    return {
        "active_session_ids": [
            session.pk
            for session in sessions
            if session.status == UseSession.Status.ACTIVE
        ],
        "sessions_without_shift": [
            session.pk for session in sessions if not session.start_shift
        ],
        "computers_without_reliable_state_history": list(excluded_computers),
    }


def segments_minutes(segments, starts_at, ends_at, *, computer_id=None):
    total = 0
    for segment_computer_id, segment_start, segment_end in segments:
        if computer_id is not None and segment_computer_id != computer_id:
            continue
        clipped = _intersection(
            segment_start,
            segment_end,
            starts_at,
            ends_at,
        )
        if clipped:
            total += interval_minutes(*clipped)
    return total


def affiliation_label(value):
    labels = dict(AffiliationType.choices)
    return labels.get(value or NOT_INFORMED, "Não informado")
