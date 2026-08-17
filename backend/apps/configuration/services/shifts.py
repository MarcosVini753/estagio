from datetime import date, time, timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.audit.models import AuditEvent
from apps.core.api.errors import ShiftReplacementConflict, ShiftReplacementInvalid

from ..models import Shift


def _snapshot(shift: Shift) -> dict:
    return {
        "id": shift.pk,
        "series_key": str(shift.series_key),
        "name": shift.name,
        "start_time": shift.start_time.isoformat(),
        "end_time": shift.end_time.isoformat(),
        "display_order": shift.display_order,
        "valid_from": shift.valid_from.isoformat(),
        "valid_until": shift.valid_until.isoformat() if shift.valid_until else None,
        "is_active": shift.is_active,
    }


def _validated_values(*, values: dict, shift: Shift | None = None) -> dict:
    if shift and shift.use_sessions.exists() and values:
        if set(values) != {"is_active"} or values["is_active"] is not False:
            raise ValidationError(
                "Turnos usados são imutáveis; apenas a desativação é permitida."
            )
    merged = {
        "name": values.get("name", shift.name if shift else ""),
        "start_time": values.get("start_time", shift.start_time if shift else None),
        "end_time": values.get("end_time", shift.end_time if shift else None),
        "display_order": values.get(
            "display_order", shift.display_order if shift else 0
        ),
        "valid_from": values.get(
            "valid_from", shift.valid_from if shift else timezone.localdate()
        ),
        "valid_until": values.get("valid_until", shift.valid_until if shift else None),
        "is_active": values.get("is_active", shift.is_active if shift else True),
    }
    if merged["start_time"] >= merged["end_time"]:
        raise ValidationError(
            {"end_time": "O horário final deve ser posterior ao horário inicial."}
        )
    if merged["valid_until"] and merged["valid_until"] < merged["valid_from"]:
        raise ValidationError(
            {"valid_until": "A validade final não pode anteceder a inicial."}
        )
    if merged["is_active"]:
        conflicts = (
            Shift.objects.select_for_update()
            .filter(
                is_active=True,
                start_time__lt=merged["end_time"],
                end_time__gt=merged["start_time"],
            )
            .filter(
                Q(valid_until__isnull=True) | Q(valid_until__gte=merged["valid_from"])
            )
        )
        if merged["valid_until"]:
            conflicts = conflicts.filter(valid_from__lte=merged["valid_until"])
        if shift:
            conflicts = conflicts.exclude(pk=shift.pk)
        if conflicts.exists():
            raise ValidationError(
                {"non_field_errors": ["O turno sobrepõe outro turno ativo."]}
            )
    return merged


@transaction.atomic
def create_shift(*, values: dict, actor_profile: str) -> Shift:
    shift = Shift.objects.create(**_validated_values(values=values))
    AuditEvent.objects.create(
        actor_profile=actor_profile,
        action="SHIFT_CREATED",
        entity_type="Shift",
        entity_id=str(shift.pk),
        new_values=_snapshot(shift),
    )
    return shift


@transaction.atomic
def update_shift(*, shift_id: int, values: dict, actor_profile: str) -> Shift:
    shift = Shift.objects.select_for_update().get(pk=shift_id)
    old_values = _snapshot(shift)
    _validated_values(values=values, shift=shift)
    for field, value in values.items():
        setattr(shift, field, value)
    shift.save(update_fields=[*values.keys(), "updated_at"])
    AuditEvent.objects.create(
        actor_profile=actor_profile,
        action="SHIFT_UPDATED",
        entity_type="Shift",
        entity_id=str(shift.pk),
        old_values=old_values,
        new_values=_snapshot(shift),
    )
    return shift


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
    if (
        effective_from <= timezone.localdate()
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

    old_values = _snapshot(shift)
    shift.valid_until = effective_from - timedelta(days=1)
    shift.save(update_fields=["valid_until", "updated_at"])
    replacement = Shift.objects.create(
        series_key=shift.series_key,
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
        new_values={**_snapshot(replacement), "shift_id": replacement.pk},
    )
    return replacement


__all__ = ["create_shift", "replace_shift", "update_shift"]
