from datetime import datetime

from django.db import transaction
from django.db.models import Q

from apps.audit.models import AuditEvent
from apps.core.api.errors import (
    SessionCorrectionInvalid,
    SessionCorrectionReasonRequired,
)
from apps.operations.models import ComputerAllocation, UseSession


def _serialize(session, first, last):
    return {
        "session": {
            "started_at": session.started_at.isoformat(),
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "status": session.status,
        },
        "first_allocation": {
            "id": first.pk,
            "started_at": first.started_at.isoformat(),
        },
        "last_allocation": {
            "id": last.pk,
            "started_at": last.started_at.isoformat(),
            "ended_at": last.ended_at.isoformat() if last.ended_at else None,
            "end_reason": last.end_reason,
        },
    }


def _overlaps_other_session(allocation, *, started_at, ended_at):
    overlaps = ComputerAllocation.objects.exclude(session=allocation.session).filter(
        computer=allocation.computer
    )
    if ended_at is not None:
        overlaps = overlaps.filter(started_at__lt=ended_at)
    return overlaps.filter(
        Q(ended_at__isnull=True) | Q(ended_at__gt=started_at)
    ).exists()


def _validate_timeline(session, allocations):
    if session.ended_at is not None and session.ended_at < session.started_at:
        raise SessionCorrectionInvalid()
    if (
        session.status == UseSession.Status.ACTIVE
        and session.ended_at is not None
        or session.status != UseSession.Status.ACTIVE
        and session.ended_at is None
    ):
        raise SessionCorrectionInvalid()
    active_allocations = [
        allocation for allocation in allocations if allocation.ended_at is None
    ]
    if session.status == UseSession.Status.ACTIVE and len(active_allocations) != 1:
        raise SessionCorrectionInvalid()
    if session.status != UseSession.Status.ACTIVE and active_allocations:
        raise SessionCorrectionInvalid()

    for index, allocation in enumerate(allocations):
        if allocation.started_at < session.started_at:
            raise SessionCorrectionInvalid()
        if (
            allocation.ended_at is not None
            and allocation.ended_at < allocation.started_at
        ):
            raise SessionCorrectionInvalid()
        if (
            session.ended_at is not None
            and allocation.ended_at is not None
            and allocation.ended_at > session.ended_at
        ):
            raise SessionCorrectionInvalid()
        if index < len(allocations) - 1 and allocation.ended_at is None:
            raise SessionCorrectionInvalid()
        if (
            index
            and allocations[index - 1].ended_at is not None
            and allocations[index - 1].ended_at > allocation.started_at
        ):
            raise SessionCorrectionInvalid()
        if _overlaps_other_session(
            allocation,
            started_at=allocation.started_at,
            ended_at=allocation.ended_at,
        ):
            raise SessionCorrectionInvalid()


@transaction.atomic
def correct_usage_session(
    *,
    session_id: int,
    actor_profile: str,
    reason: str,
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
    last_allocation_started_at: datetime | None = None,
    last_allocation_ended_at: datetime | None = None,
) -> UseSession:
    correction_reason = reason.strip()
    if not correction_reason:
        raise SessionCorrectionReasonRequired()

    session = UseSession.objects.select_for_update().get(pk=session_id)
    allocations = list(session.allocations.select_for_update().order_by("sequence"))
    if not allocations:
        raise SessionCorrectionInvalid()
    first = allocations[0]
    last = allocations[-1]
    old_values = _serialize(session, first, last)

    if (
        first.pk == last.pk
        and started_at is not None
        and last_allocation_started_at is not None
        and started_at != last_allocation_started_at
    ):
        raise SessionCorrectionInvalid()
    if (
        ended_at is not None
        and last_allocation_ended_at is not None
        and ended_at != last_allocation_ended_at
    ):
        raise SessionCorrectionInvalid()

    if started_at is not None:
        session.started_at = started_at
        first.started_at = started_at
    if last_allocation_started_at is not None:
        last.started_at = last_allocation_started_at
    if ended_at is not None:
        session.ended_at = ended_at
        session.status = UseSession.Status.FINISHED
        session.exit_recorded_by_profile = actor_profile
        last.ended_at = ended_at
        last.end_reason = ComputerAllocation.EndReason.ADMIN_CORRECTION
    elif last_allocation_ended_at is not None:
        last.ended_at = last_allocation_ended_at

    _validate_timeline(session, allocations)

    session.save(
        update_fields=[
            "started_at",
            "ended_at",
            "status",
            "exit_recorded_by_profile",
            "updated_at",
        ]
    )
    for allocation in {first.pk: first, last.pk: last}.values():
        allocation.save(
            update_fields=[
                "started_at",
                "ended_at",
                "end_reason",
                "updated_at",
            ]
        )

    AuditEvent.objects.create(
        actor_profile=actor_profile,
        action="USAGE_SESSION_CORRECTED",
        entity_type="UseSession",
        entity_id=str(session.pk),
        old_values=old_values,
        new_values=_serialize(session, first, last),
        reason=correction_reason,
    )
    return session
