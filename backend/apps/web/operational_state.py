from datetime import datetime

from django.utils import timezone

from apps.access.services import get_demo_user_reference
from apps.operations.services.deadlines import ReconcileScope, reconcile_deadlines


def reconcile_room_user_state(
    request,
    *,
    now: datetime | None = None,
    computer_ids=(),
) -> datetime:
    """Reconcilia somente os dados observados pela leitura do usuário."""

    current = now or timezone.now()
    reference = get_demo_user_reference(request)
    reconcile_deadlines(
        now=current,
        scope=ReconcileScope(
            computer_ids=tuple(computer_ids) or None,
            user_references=(reference,) if reference else None,
        ),
    )
    return current


def reconcile_operational_state(
    *,
    now: datetime | None = None,
    period: tuple[datetime, datetime] | None = None,
) -> datetime:
    """Reconcilia o estado global antes de painéis e relatórios autorizados."""

    current = now or timezone.now()
    reconcile_deadlines(
        now=current,
        scope=ReconcileScope(period=period) if period else None,
    )
    return current


__all__ = ["reconcile_operational_state", "reconcile_room_user_state"]
