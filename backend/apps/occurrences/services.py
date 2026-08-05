from django.db import transaction
from django.utils import timezone

from apps.computers.models import Computer
from apps.core.api.errors import (
    OccurrenceLinkInvalid,
    OccurrenceResolutionNotesRequired,
    OccurrenceTransitionInvalid,
)
from apps.core.enums import DemoProfile
from apps.operations.models import ComputerAllocation, UseSession

from .models import Occurrence

ALLOWED_TRANSITIONS = {
    Occurrence.Status.OPEN: {
        Occurrence.Status.IN_REVIEW,
        Occurrence.Status.CANCELLED,
    },
    Occurrence.Status.IN_REVIEW: {
        Occurrence.Status.RESOLVED,
        Occurrence.Status.CANCELLED,
    },
}


def create_occurrence(
    *,
    actor_profile: str,
    actor_reference: str,
    description: str,
    computer: Computer | None = None,
    session: UseSession | None = None,
    allocation: ComputerAllocation | None = None,
) -> Occurrence:
    if allocation is not None:
        if session is not None and allocation.session_id != session.pk:
            raise OccurrenceLinkInvalid()
        if computer is not None and allocation.computer_id != computer.pk:
            raise OccurrenceLinkInvalid()
        session = session or allocation.session
        computer = computer or allocation.computer
    if (
        session is not None
        and computer is not None
        and not session.allocations.filter(computer=computer).exists()
    ):
        raise OccurrenceLinkInvalid()
    if (
        actor_profile == DemoProfile.ROOM_USER
        and session is not None
        and session.user_reference != actor_reference
    ):
        raise OccurrenceLinkInvalid()

    return Occurrence.objects.create(
        reported_by_reference=(
            session.user_reference if session is not None else actor_reference
        ),
        computer=computer,
        session=session,
        allocation=allocation,
        description=description.strip(),
    )


@transaction.atomic
def transition_occurrence(
    *,
    occurrence_id: int,
    status: str,
    actor_profile: str,
    resolution_notes: str = "",
) -> Occurrence:
    occurrence = Occurrence.objects.select_for_update().get(pk=occurrence_id)
    if status not in ALLOWED_TRANSITIONS.get(occurrence.status, set()):
        raise OccurrenceTransitionInvalid()

    notes = resolution_notes.strip()
    if status == Occurrence.Status.RESOLVED and not notes:
        raise OccurrenceResolutionNotesRequired()

    occurrence.status = status
    if status == Occurrence.Status.RESOLVED:
        occurrence.resolved_by_profile = actor_profile
        occurrence.resolution_notes = notes
        occurrence.resolved_at = timezone.now()
    occurrence.save(
        update_fields=[
            "status",
            "resolved_by_profile",
            "resolution_notes",
            "resolved_at",
            "updated_at",
        ]
    )
    return occurrence
