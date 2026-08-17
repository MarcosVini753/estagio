from dataclasses import dataclass
from datetime import datetime

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.computers.models import Computer
from apps.computers.services import (
    record_operational_state_change,
    validate_operational_state_change,
)
from apps.operations.models import ComputerAllocation, Reservation, UseSession
from apps.operations.services.deadlines import reconcile_computer_deadlines
from apps.operations.services.reservations import cancel_locked_reservation


@dataclass(frozen=True)
class ComputerStateChangeResult:
    computer: Computer
    impact: dict


def _candidate_is_available_for_session(
    *,
    candidate: Computer,
    session: UseSession,
    starts_at: datetime,
) -> bool:
    if candidate.operational_state != Computer.OperationalState.AVAILABLE:
        return False
    if starts_at >= session.planned_ends_at:
        return False
    if ComputerAllocation.objects.filter(
        computer=candidate,
        ended_at__isnull=True,
        session__status=UseSession.Status.ACTIVE,
        session__planned_starts_at__lt=session.planned_ends_at,
        session__planned_ends_at__gt=starts_at,
    ).exists():
        return False
    return not (
        Reservation.objects.filter(
            status=Reservation.Status.CONFIRMED,
            starts_at__lt=session.planned_ends_at,
            ends_at__gt=starts_at,
        )
        .filter(Q(computer=candidate) | Q(user_reference=session.user_reference))
        .exists()
    )


def _candidate_is_available_for_reservation(
    *,
    candidate: Computer,
    reservation: Reservation,
) -> bool:
    if candidate.operational_state != Computer.OperationalState.AVAILABLE:
        return False
    if ComputerAllocation.objects.filter(
        computer=candidate,
        ended_at__isnull=True,
        session__status=UseSession.Status.ACTIVE,
        session__planned_starts_at__lt=reservation.ends_at,
        session__planned_ends_at__gt=reservation.starts_at,
    ).exists():
        return False
    return (
        not Reservation.objects.filter(
            computer=candidate,
            status=Reservation.Status.CONFIRMED,
            starts_at__lt=reservation.ends_at,
            ends_at__gt=reservation.starts_at,
        )
        .exclude(pk=reservation.pk)
        .exists()
    )


def _resolve_active_session(
    *,
    source: Computer,
    candidates: list[Computer],
    actor_profile: str,
    reason: str,
    current: datetime,
) -> dict | None:
    allocation = (
        ComputerAllocation.objects.select_for_update()
        .filter(
            computer=source,
            ended_at__isnull=True,
            session__status=UseSession.Status.ACTIVE,
        )
        .order_by("pk")
        .first()
    )
    if allocation is None:
        return None

    session = UseSession.objects.select_for_update().get(pk=allocation.session_id)
    destination = next(
        (
            candidate
            for candidate in candidates
            if _candidate_is_available_for_session(
                candidate=candidate,
                session=session,
                starts_at=current,
            )
        ),
        None,
    )
    allocation.ended_at = current
    allocation.switch_reason = reason

    if destination is not None:
        allocation.end_reason = ComputerAllocation.EndReason.COMPUTER_UNAVAILABLE
        allocation.save(
            update_fields=["ended_at", "end_reason", "switch_reason", "updated_at"]
        )
        ComputerAllocation.objects.create(
            session=session,
            computer=destination,
            sequence=allocation.sequence + 1,
            started_at=current,
        )
        return {
            "session_id": session.pk,
            "action": "REALLOCATED",
            "from_computer_id": source.pk,
            "to_computer_id": destination.pk,
        }

    allocation.end_reason = ComputerAllocation.EndReason.COMPUTER_UNAVAILABLE
    allocation.save(
        update_fields=["ended_at", "end_reason", "switch_reason", "updated_at"]
    )
    session.ended_at = current
    session.status = UseSession.Status.FINISHED
    session.exit_recorded_by_profile = actor_profile
    session.save(
        update_fields=[
            "ended_at",
            "status",
            "exit_recorded_by_profile",
            "updated_at",
        ]
    )
    AuditEvent.objects.create(
        actor_profile=actor_profile,
        action="USAGE_SESSION_FINISHED_COMPUTER_UNAVAILABLE",
        entity_type="UseSession",
        entity_id=str(session.pk),
        old_values={"status": UseSession.Status.ACTIVE},
        new_values={
            "status": UseSession.Status.FINISHED,
            "ended_at": current.isoformat(),
        },
        reason=reason,
    )
    return {
        "session_id": session.pk,
        "action": "FINISHED",
        "from_computer_id": source.pk,
        "to_computer_id": None,
    }


def _resolve_reservations(
    *,
    source: Computer,
    candidates: list[Computer],
    actor_profile: str,
    reason: str,
    current: datetime,
) -> dict:
    reservations = list(
        Reservation.objects.select_for_update()
        .filter(
            computer=source,
            status=Reservation.Status.CONFIRMED,
            check_in_deadline_at__gte=current,
        )
        .order_by("starts_at", "pk")
    )
    reallocated = []
    cancelled = []
    for reservation in reservations:
        destination = next(
            (
                candidate
                for candidate in candidates
                if _candidate_is_available_for_reservation(
                    candidate=candidate,
                    reservation=reservation,
                )
            ),
            None,
        )
        if destination is None:
            cancel_locked_reservation(
                reservation=reservation,
                actor_profile=actor_profile,
                reason=reason,
                cancelled_at=current,
            )
            cancelled.append({"reservation_id": reservation.pk})
            continue

        old_computer_id = reservation.computer_id
        reservation.computer = destination
        reservation.save(update_fields=["computer", "updated_at"])
        AuditEvent.objects.create(
            actor_profile=actor_profile,
            action="RESERVATION_REALLOCATED",
            entity_type="Reservation",
            entity_id=str(reservation.pk),
            old_values={"computer_id": old_computer_id},
            new_values={"computer_id": destination.pk},
            reason=reason,
        )
        reallocated.append(
            {
                "reservation_id": reservation.pk,
                "from_computer_id": old_computer_id,
                "to_computer_id": destination.pk,
            }
        )
    return {"reallocated": reallocated, "cancelled": cancelled}


@transaction.atomic
def change_computer_operational_state(
    *,
    computer_id: int,
    new_state: str,
    actor_profile: str,
    reason: str = "",
    now: datetime | None = None,
) -> ComputerStateChangeResult:
    current = now or timezone.now()
    reconcile_computer_deadlines(computer_id, current)

    computers = list(Computer.objects.select_for_update().order_by("pk"))
    source = next(computer for computer in computers if computer.pk == computer_id)
    normalized_reason = validate_operational_state_change(
        computer=source,
        new_state=new_state,
        reason=reason,
    )
    impact = {
        "active_session": None,
        "reservations": {"reallocated": [], "cancelled": []},
    }
    becomes_unavailable = (
        source.operational_state == Computer.OperationalState.AVAILABLE
        and new_state
        in {
            Computer.OperationalState.MAINTENANCE,
            Computer.OperationalState.INACTIVE,
        }
    )
    if becomes_unavailable:
        candidates = [computer for computer in computers if computer.pk != source.pk]
        operational_reason = f"{source.code} indisponibilizado: {normalized_reason}"
        impact["active_session"] = _resolve_active_session(
            source=source,
            candidates=candidates,
            actor_profile=actor_profile,
            reason=operational_reason,
            current=current,
        )
        impact["reservations"] = _resolve_reservations(
            source=source,
            candidates=candidates,
            actor_profile=actor_profile,
            reason=operational_reason,
            current=current,
        )

    previous_state = source.operational_state
    record_operational_state_change(
        computer=source,
        new_state=new_state,
        actor_profile=actor_profile,
        reason=normalized_reason,
    )
    AuditEvent.objects.create(
        actor_profile=actor_profile,
        action="COMPUTER_OPERATIONAL_STATE_CHANGED",
        entity_type="Computer",
        entity_id=str(source.pk),
        old_values={"operational_state": previous_state},
        new_values={"operational_state": new_state, "impact": impact},
        reason=normalized_reason,
    )
    return ComputerStateChangeResult(computer=source, impact=impact)
