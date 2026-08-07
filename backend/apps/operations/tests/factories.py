from datetime import timedelta

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.configuration.models import BookingPolicy
from apps.configuration.selectors import get_booking_policy_for_date
from apps.operations.models import Reservation, UseSession
from apps.operations.rules import (
    LATE_CHECK_IN_TOLERANCE_MINUTES,
    LATE_CHECK_OUT_TOLERANCE_MINUTES,
    SLOT_DURATION_MINUTES,
)


def create_reservation(**values):
    starts_at = values["starts_at"]
    ends_at = values["ends_at"]
    if isinstance(starts_at, str):
        starts_at = parse_datetime(starts_at)
        values["starts_at"] = starts_at
    if isinstance(ends_at, str):
        ends_at = parse_datetime(ends_at)
        values["ends_at"] = ends_at
    values.setdefault(
        "check_in_deadline_at",
        starts_at + timedelta(minutes=LATE_CHECK_IN_TOLERANCE_MINUTES),
    )
    values.setdefault(
        "exit_deadline_at",
        ends_at + timedelta(minutes=LATE_CHECK_OUT_TOLERANCE_MINUTES),
    )
    if "booking_policy" not in values:
        policy = get_booking_policy_for_date(timezone.localdate(starts_at))
        if policy is None:
            policy = BookingPolicy.objects.order_by("valid_from", "created_at").first()
        if policy is None:
            policy = BookingPolicy.objects.create(
                valid_from=timezone.localdate(starts_at)
            )
        values["booking_policy"] = policy
    return Reservation.objects.create(**values)


def create_use_session(**values):
    for field in (
        "started_at",
        "ended_at",
        "planned_starts_at",
        "planned_ends_at",
        "exit_deadline_at",
    ):
        if isinstance(values.get(field), str):
            values[field] = parse_datetime(values[field])
    started_at = values.setdefault("started_at", timezone.now())
    reservation = values.get("reservation")
    planned_starts_at = values.setdefault(
        "planned_starts_at",
        reservation.starts_at if reservation else started_at,
    )
    planned_ends_at = values.setdefault(
        "planned_ends_at",
        (
            reservation.ends_at
            if reservation
            else values.get("ended_at")
            or planned_starts_at + timedelta(minutes=SLOT_DURATION_MINUTES)
        ),
    )
    values.setdefault(
        "exit_deadline_at",
        (
            reservation.exit_deadline_at
            if reservation
            else planned_ends_at + timedelta(minutes=LATE_CHECK_OUT_TOLERANCE_MINUTES)
        ),
    )
    return UseSession.objects.create(**values)
