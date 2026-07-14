from django.db import transaction

from apps.core.api.errors import ComputerStateUnchanged, StateChangeReasonRequired

from .models import Computer, ComputerOperationalStateChange


@transaction.atomic
def change_operational_state(
    *,
    computer_id: int,
    new_state: str,
    actor_profile: str,
    reason: str = "",
) -> Computer:
    computer = Computer.objects.select_for_update().get(pk=computer_id)
    normalized_reason = reason.strip()

    if computer.operational_state == new_state:
        raise ComputerStateUnchanged()

    if (
        new_state
        in {
            Computer.OperationalState.MAINTENANCE,
            Computer.OperationalState.INACTIVE,
        }
        and not normalized_reason
    ):
        raise StateChangeReasonRequired()

    previous_state = computer.operational_state
    computer.operational_state = new_state
    computer.save(update_fields=["operational_state", "updated_at"])
    ComputerOperationalStateChange.objects.create(
        computer=computer,
        previous_state=previous_state,
        new_state=new_state,
        actor_profile=actor_profile,
        reason=normalized_reason,
    )
    return computer
