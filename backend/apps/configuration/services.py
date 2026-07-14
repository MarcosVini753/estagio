from django.db import transaction
from django.utils import timezone

from .models import BookingPolicy

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
