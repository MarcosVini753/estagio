from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditEvent

from ..models import BookingPolicy, ReportConfiguration

BOOKING_POLICY_FIELDS = (
    "cancellation_limit_minutes",
    "max_future_reservations_per_user",
)
REPORT_CONFIGURATION_FIELDS = (
    "default_format",
    "group_by_shift",
    "include_occurrences",
)


def _booking_policy_snapshot(policy: BookingPolicy | None) -> dict:
    if policy is None:
        return {}
    return {
        "id": policy.pk,
        "cancellation_limit_minutes": policy.cancellation_limit_minutes,
        "max_future_reservations_per_user": policy.max_future_reservations_per_user,
        "valid_from": policy.valid_from.isoformat(),
        "valid_until": policy.valid_until.isoformat() if policy.valid_until else None,
    }


@transaction.atomic
def update_current_booking_policy(*, values: dict, actor_profile: str) -> BookingPolicy:
    today = timezone.localdate()
    policies = list(
        BookingPolicy.objects.select_for_update().order_by(
            "valid_from", "created_at", "pk"
        )
    )
    base = policies[-1] if policies else None
    old_values = _booking_policy_snapshot(base)

    if base and base.valid_from >= today and not base.reservations.exists():
        for field, value in values.items():
            setattr(base, field, value)
        base.save(update_fields=[*values.keys(), "updated_at"])
        policy = base
    else:
        merged = {
            field: values.get(
                field,
                getattr(base, field)
                if base
                else BookingPolicy._meta.get_field(field).default,
            )
            for field in BOOKING_POLICY_FIELDS
        }
        valid_from = (
            max(today, base.valid_from + timedelta(days=1))
            if base and base.valid_from >= today
            else today
        )
        if base and (base.valid_until is None or base.valid_until >= valid_from):
            base.valid_until = valid_from - timedelta(days=1)
            base.save(update_fields=["valid_until", "updated_at"])
        policy = BookingPolicy.objects.create(**merged, valid_from=valid_from)

    AuditEvent.objects.create(
        actor_profile=actor_profile,
        action="BOOKING_POLICY_UPDATED",
        entity_type="BookingPolicy",
        entity_id=str(policy.pk),
        old_values=old_values,
        new_values=_booking_policy_snapshot(policy),
    )
    return policy


@transaction.atomic
def update_report_configuration(
    *, values: dict, actor_profile: str
) -> ReportConfiguration:
    configuration = (
        ReportConfiguration.objects.select_for_update().filter(is_active=True).first()
    )
    old_values = (
        {field: getattr(configuration, field) for field in REPORT_CONFIGURATION_FIELDS}
        if configuration
        else {}
    )
    if configuration is None:
        configuration = ReportConfiguration.objects.create(**values)
    else:
        for field, value in values.items():
            setattr(configuration, field, value)
        configuration.save(update_fields=[*values.keys(), "updated_at"])
    AuditEvent.objects.create(
        actor_profile=actor_profile,
        action="REPORT_CONFIGURATION_UPDATED",
        entity_type="ReportConfiguration",
        entity_id=str(configuration.pk),
        old_values=old_values,
        new_values={
            field: getattr(configuration, field)
            for field in REPORT_CONFIGURATION_FIELDS
        },
    )
    return configuration


__all__ = ["update_current_booking_policy", "update_report_configuration"]
