from apps.core.api.errors import ComputerStateUnchanged, StateChangeReasonRequired

from .models import Computer, ComputerOperationalStateChange


def validate_operational_state_change(
    *,
    computer: Computer,
    new_state: str,
    reason: str = "",
) -> str:
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
    return normalized_reason


def record_operational_state_change(
    *,
    computer: Computer,
    new_state: str,
    actor_profile: str,
    reason: str = "",
) -> Computer:
    normalized_reason = validate_operational_state_change(
        computer=computer,
        new_state=new_state,
        reason=reason,
    )

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
