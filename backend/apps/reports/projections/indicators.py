from collections import defaultdict
from datetime import datetime, time, timedelta

from django.utils import timezone

from apps.occurrences.models import Occurrence

from .common import (
    NOT_INFORMED,
    REPORT_TIME_ZONE,
    affiliation_label,
    build_occupancy,
    build_summary,
    inclusive_period_bounds,
    interval_minutes,
    overlap_minutes,
    segments_minutes,
    shift_columns,
    standard_warnings,
)


def _metric_rows(
    sessions,
    allocations,
    key_getter,
    *,
    period_start,
    period_end,
    now,
    label_getter=None,
):
    grouped_sessions = defaultdict(list)
    for session in sessions:
        grouped_sessions[key_getter(session)].append(session)
    allocated_by_key = defaultdict(int)
    for allocation in allocations:
        key = key_getter(allocation.session)
        allocated_by_key[key] += overlap_minutes(
            allocation.started_at,
            allocation.ended_at,
            period_start,
            period_end,
            now=now,
        )
    rows = []
    for key in grouped_sessions.keys() | allocated_by_key.keys():
        values = grouped_sessions[key]
        rows.append(
            {
                "key": key,
                "label": label_getter(key) if label_getter else key,
                "visits": len(values),
                "distinct_users": len({item.user_reference for item in values}),
                "allocated_minutes": allocated_by_key[key],
            }
        )
    return sorted(rows, key=lambda item: (-item["visits"], str(item["label"])))


def _minutes_by_shift(allocations, period_start, period_end, now):
    totals = defaultdict(int)
    for allocation in allocations:
        shift = allocation.session.start_shift
        key = str(shift.series_key) if shift else NOT_INFORMED
        totals[key] += overlap_minutes(
            allocation.started_at,
            allocation.ended_at,
            period_start,
            period_end,
            now=now,
        )
    return totals


def _slot_totals(segments):
    totals = defaultdict(int)
    for _, segment_start, segment_end in segments:
        cursor = timezone.localtime(segment_start, REPORT_TIME_ZONE)
        cursor = cursor.replace(
            minute=cursor.minute - cursor.minute % 15,
            second=0,
            microsecond=0,
        )
        while cursor < segment_end:
            slot_end = cursor + timedelta(minutes=15)
            totals[cursor.hour * 4 + cursor.minute // 15] += interval_minutes(
                max(segment_start, cursor),
                min(segment_end, slot_end),
            )
            cursor = slot_end
    return totals


def _time_slots(occupancy):
    allocated_by_slot = _slot_totals(occupancy.allocated_segments)
    available_by_slot = _slot_totals(occupancy.available_segments)
    rows = []
    for slot_number in range(96):
        allocated = allocated_by_slot[slot_number]
        available = available_by_slot[slot_number]
        if allocated or available:
            starts_at = time(slot_number // 4, slot_number % 4 * 15)
            rows.append(
                {
                    "starts_at": starts_at.isoformat(timespec="minutes"),
                    "allocated_minutes": allocated,
                    "available_minutes": available,
                    "occupancy_rate_percent": (
                        round(allocated * 100 / available, 2) if available else None
                    ),
                }
            )
    return rows


def build_indicators_report(
    *,
    starts_on,
    ends_on,
    sessions,
    allocations,
    reservations,
    occurrences,
    shifts,
    operating_days,
    computers,
    now,
):
    period_start, period_end = inclusive_period_bounds(starts_on, ends_on)
    sessions = list(sessions)
    allocations = list(allocations)
    reservations = list(reservations)
    occurrences = list(occurrences)
    shifts = list(shifts)
    operating_days = list(operating_days)
    computers = list(computers)
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
        computers=computers,
        allocations=allocations,
    )
    classified_sessions = [*sessions, *(item.session for item in allocations)]
    columns = shift_columns(shifts, classified_sessions)
    visit_totals = defaultdict(int)
    for session in sessions:
        key = (
            str(session.start_shift.series_key) if session.start_shift else NOT_INFORMED
        )
        visit_totals[key] += 1
    allocated_by_shift = _minutes_by_shift(
        allocations,
        period_start,
        period_end,
        now,
    )
    shift_labels = {item["series_key"]: item["name"] for item in columns}
    shift_labels[NOT_INFORMED] = "Não informado"
    shift_keys = [item["series_key"] for item in columns] + [NOT_INFORMED]
    by_shift = [
        {
            "key": key,
            "label": shift_labels[key],
            "visits": visit_totals[key],
            "allocated_minutes": allocated_by_shift[key],
        }
        for key in shift_keys
    ]

    sessions_by_computer = defaultdict(set)
    for allocation in allocations:
        sessions_by_computer[allocation.computer_id].add(allocation.session_id)
    occurrences_by_computer = defaultdict(int)
    for occurrence in occurrences:
        if occurrence.computer_id:
            occurrences_by_computer[occurrence.computer_id] += 1
    by_computer = []
    for row in occupancy.computers:
        by_computer.append(
            {
                **row,
                "visits": len(sessions_by_computer[row["computer_id"]]),
                "occurrences": occurrences_by_computer[row["computer_id"]],
            }
        )
    by_computer.sort(key=lambda item: (-item["allocated_minutes"], item["code"]))

    by_day = []
    for operating_day in operating_days:
        day_start = timezone.make_aware(
            datetime.combine(operating_day.date, time.min),
            REPORT_TIME_ZONE,
        )
        day_end = day_start + timedelta(days=1)
        visits = sum(
            timezone.localtime(session.started_at, REPORT_TIME_ZONE).date()
            == operating_day.date
            for session in sessions
        )
        allocated = segments_minutes(
            occupancy.allocated_segments,
            day_start,
            day_end,
        )
        available = segments_minutes(
            occupancy.available_segments,
            day_start,
            day_end,
        )
        by_day.append(
            {
                "date": operating_day.date.isoformat(),
                "visits": visits,
                "allocated_minutes": allocated,
                "available_minutes": available,
                "occupancy_rate_percent": (
                    round(allocated * 100 / available, 2) if available else None
                ),
            }
        )

    by_time_slot = _time_slots(occupancy)
    return {
        "period": {
            "starts_on": starts_on.isoformat(),
            "ends_on": ends_on.isoformat(),
            "starts_at": period_start.isoformat(),
            "ends_at": period_end.isoformat(),
        },
        "summary": summary,
        "occupancy": occupancy.payload,
        "by_shift": by_shift,
        "by_affiliation": _metric_rows(
            sessions,
            allocations,
            lambda item: item.affiliation_type or NOT_INFORMED,
            period_start=period_start,
            period_end=period_end,
            now=now,
            label_getter=affiliation_label,
        ),
        "by_institutional_unit": _metric_rows(
            sessions,
            allocations,
            lambda item: item.institutional_unit.strip() or NOT_INFORMED,
            period_start=period_start,
            period_end=period_end,
            now=now,
            label_getter=(lambda key: "Não informado" if key == NOT_INFORMED else key),
        ),
        "by_computer": by_computer,
        "by_day": by_day,
        "by_time_slot": by_time_slot,
        "busiest_days": sorted(
            by_day,
            key=lambda item: (
                -item["visits"],
                -item["allocated_minutes"],
                item["date"],
            ),
        )[:10],
        "busiest_time_slots": sorted(
            by_time_slot,
            key=lambda item: (-item["allocated_minutes"], item["starts_at"]),
        )[:10],
        "reservations_by_status": summary["reservations_by_status"],
        "occurrences_by_status": {
            status: sum(item.status == status for item in occurrences)
            for status in Occurrence.Status.values
        },
        "warnings": standard_warnings(sessions, excluded),
    }
