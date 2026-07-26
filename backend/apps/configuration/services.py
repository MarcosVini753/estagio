from datetime import date, time, timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.core.api.errors import ShiftReplacementConflict, ShiftReplacementInvalid

from .models import BookingPolicy, Shift

BOOKING_POLICY_FIELDS = (
    "slot_duration_minutes",
    "check_in_tolerance_minutes",
    "cancellation_limit_minutes",
    "max_future_reservations_per_user",
)


@transaction.atomic
def update_active_booking_policy(*, values: dict) -> BookingPolicy:
    today = timezone.localdate()
    current = (
        BookingPolicy.objects.select_for_update()
        .filter(is_active=True)
        .order_by("-valid_from", "-created_at")
        .first()
    )

    if current and current.valid_from == today:
        for field, value in values.items():
            setattr(current, field, value)
        current.save(update_fields=[*values.keys(), "updated_at"])
        return current

    merged = {
        field: values.get(
            field,
            getattr(current, field)
            if current
            else BookingPolicy._meta.get_field(field).default,
        )
        for field in BOOKING_POLICY_FIELDS
    }

    if current:
        current.is_active = False
        current.save(update_fields=["is_active", "updated_at"])

    return BookingPolicy.objects.create(
        **merged,
        valid_from=today,
        is_active=True,
    )


@transaction.atomic
def replace_shift(
    *,
    shift_id: int,
    effective_from: date,
    name: str,
    start_time: time,
    end_time: time,
    display_order: int,
    actor_profile: str,
) -> Shift:
    shift = Shift.objects.select_for_update().get(pk=shift_id)
    today = timezone.localdate()

    if (
        effective_from <= today
        or effective_from <= shift.valid_from
        or shift.valid_until is not None
    ):
        raise ShiftReplacementInvalid()

    conflicts = (
        Shift.objects.select_for_update()
        .filter(
            is_active=True,
            start_time__lt=end_time,
            end_time__gt=start_time,
        )
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=effective_from))
        .exclude(pk=shift.pk)
    )
    if conflicts.exists():
        raise ShiftReplacementConflict()

    old_values = {
        "name": shift.name,
        "start_time": shift.start_time.isoformat(),
        "end_time": shift.end_time.isoformat(),
        "display_order": shift.display_order,
        "valid_from": shift.valid_from.isoformat(),
        "valid_until": shift.valid_until.isoformat() if shift.valid_until else None,
    }
    shift.valid_until = effective_from - timedelta(days=1)
    shift.save(update_fields=["valid_until", "updated_at"])

    replacement = Shift.objects.create(
        name=name,
        start_time=start_time,
        end_time=end_time,
        display_order=display_order,
        valid_from=effective_from,
    )
    AuditEvent.objects.create(
        actor_profile=actor_profile,
        action="SHIFT_REPLACED",
        entity_type="Shift",
        entity_id=str(shift.pk),
        old_values=old_values,
        new_values={
            "shift_id": replacement.pk,
            "name": replacement.name,
            "start_time": replacement.start_time.isoformat(),
            "end_time": replacement.end_time.isoformat(),
            "display_order": replacement.display_order,
            "valid_from": replacement.valid_from.isoformat(),
        },
    )
    return replacement
