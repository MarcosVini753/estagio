from datetime import datetime, timedelta

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.computers.models import Computer
from apps.configuration.calendar import (
    is_open_at,
    lock_operating_date,
    resolve_operating_day,
)
from apps.configuration.selectors import get_shifts_for_date
from apps.core.api.errors import (
    ReservationCheckInUnavailable,
    RoomClosed,
    UsageSessionConflict,
    UsageSessionIdentityRequired,
    UsageSessionNotActive,
    UsageSessionNotAllowed,
    UsageSessionReasonRequired,
)
from apps.core.enums import AffiliationType, DemoProfile
from apps.operations.models import ComputerAllocation, Reservation, UseSession
from apps.operations.rules import (
    EARLY_CHECK_IN_TOLERANCE_MINUTES,
    LATE_CHECK_OUT_TOLERANCE_MINUTES,
)
from apps.operations.services.deadlines import (
    expire_locked_session,
    reconcile_computer_deadlines,
)
from apps.operations.services.reservations import lock_user_reference
from apps.operations.slotting import validate_immediate_planned_end

OPERATIONAL_PROFILES = {
    DemoProfile.ROOM_MONITOR,
    DemoProfile.LIBRARY_SUPERVISOR,
    DemoProfile.SYSTEM_ADMIN,
}


def _shift_at(current: datetime):
    local = timezone.localtime(current)
    return (
        get_shifts_for_date(local.date())
        .filter(start_time__lte=local.time(), end_time__gt=local.time())
        .first()
    )


def _reservation_blocks_interval(
    *,
    computer_id: int,
    user_reference: str,
    starts_at: datetime,
    ends_at: datetime,
) -> bool:
    return (
        Reservation.objects.filter(
            status=Reservation.Status.CONFIRMED,
            starts_at__lt=ends_at,
            ends_at__gt=starts_at,
        )
        .filter(Q(computer_id=computer_id) | Q(user_reference=user_reference))
        .exists()
    )


def _planned_allocation_blocks_interval(
    *,
    computer_id: int,
    starts_at: datetime,
    ends_at: datetime,
) -> bool:
    return ComputerAllocation.objects.filter(
        computer_id=computer_id,
        ended_at__isnull=True,
        session__status=UseSession.Status.ACTIVE,
        session__planned_starts_at__lt=ends_at,
        session__planned_ends_at__gt=starts_at,
    ).exists()


def _validate_identity(
    *,
    actor_profile: str,
    actor_reference: str,
    user_reference: str | None,
    affiliation_type: str | None,
    institutional_unit: str | None,
) -> tuple[str, str, str]:
    if actor_profile == DemoProfile.ROOM_USER:
        if (
            not actor_reference
            or affiliation_type not in AffiliationType.values
            or affiliation_type == AffiliationType.NOT_INFORMED
            or not institutional_unit
        ):
            raise UsageSessionIdentityRequired()
        return actor_reference, affiliation_type, institutional_unit
    if (
        not user_reference
        or affiliation_type not in AffiliationType.values
        or affiliation_type == AffiliationType.NOT_INFORMED
        or not institutional_unit
    ):
        raise UsageSessionIdentityRequired()
    return user_reference, affiliation_type, institutional_unit


def _get_active_session(
    *, session_id: int, actor_profile: str, actor_reference: str
) -> UseSession:
    session = UseSession.objects.select_for_update().get(pk=session_id)
    if session.status != UseSession.Status.ACTIVE:
        raise UsageSessionNotActive()
    if (
        actor_profile not in OPERATIONAL_PROFILES
        and actor_reference != session.user_reference
    ):
        raise UsageSessionNotAllowed()
    return session


def start_usage_session(
    *,
    computer_id: int,
    actor_profile: str,
    actor_reference: str,
    reservation_id: int | None = None,
    planned_ends_at: datetime | None = None,
    user_reference: str | None = None,
    affiliation_type: str | None = None,
    institutional_unit: str | None = None,
    now: datetime | None = None,
) -> UseSession:
    current = now or timezone.now()
    if reservation_id is not None:
        reconciliation_user_reference = (
            Reservation.objects.filter(pk=reservation_id)
            .values_list("user_reference", flat=True)
            .first()
        )
    elif actor_profile == DemoProfile.ROOM_USER:
        reconciliation_user_reference = actor_reference
    else:
        reconciliation_user_reference = user_reference
    computer_ids = {computer_id}
    if reconciliation_user_reference:
        computer_ids.update(
            Reservation.objects.filter(
                user_reference=reconciliation_user_reference,
                status=Reservation.Status.CONFIRMED,
                check_in_deadline_at__lt=current,
            ).values_list("computer_id", flat=True)
        )
        computer_ids.update(
            ComputerAllocation.objects.filter(
                session__user_reference=reconciliation_user_reference,
                session__status=UseSession.Status.ACTIVE,
                ended_at__isnull=True,
            ).values_list("computer_id", flat=True)
        )
    for target_id in sorted(computer_ids):
        reconcile_computer_deadlines(target_id, current)
    return _start_usage_session(
        computer_id=computer_id,
        actor_profile=actor_profile,
        actor_reference=actor_reference,
        reservation_id=reservation_id,
        planned_ends_at=planned_ends_at,
        user_reference=user_reference,
        affiliation_type=affiliation_type,
        institutional_unit=institutional_unit,
        current=current,
    )


@transaction.atomic
def _start_usage_session(
    *,
    computer_id: int,
    actor_profile: str,
    actor_reference: str,
    reservation_id: int | None,
    planned_ends_at: datetime | None,
    user_reference: str | None,
    affiliation_type: str | None,
    institutional_unit: str | None,
    current: datetime,
) -> UseSession:
    lock_operating_date(timezone.localdate(current))
    reservation = None

    if reservation_id is not None and planned_ends_at is not None:
        raise UsageSessionConflict("O fim é definido pela reserva informada.")
    if reservation_id is None and planned_ends_at is None:
        raise UsageSessionConflict("Informe o horário planejado de saída.")

    if reservation_id is not None:
        reservation_preview = Reservation.objects.get(pk=reservation_id)
        user_reference = reservation_preview.user_reference
        affiliation_type = reservation_preview.affiliation_type
        institutional_unit = reservation_preview.institutional_unit
    else:
        user_reference, affiliation_type, institutional_unit = _validate_identity(
            actor_profile=actor_profile,
            actor_reference=actor_reference,
            user_reference=user_reference,
            affiliation_type=affiliation_type,
            institutional_unit=institutional_unit,
        )
    operating_day = resolve_operating_day(timezone.localdate(current))
    if not is_open_at(operating_day, current):
        raise RoomClosed()

    lock_user_reference(user_reference)
    computer = Computer.objects.select_for_update().get(pk=computer_id)
    if reservation_id is not None:
        reservation = Reservation.objects.select_for_update().get(pk=reservation_id)
        if (
            reservation.status != Reservation.Status.CONFIRMED
            or reservation.computer_id != computer_id
            or (
                actor_profile == DemoProfile.ROOM_USER
                and actor_reference != reservation.user_reference
            )
            or not (
                reservation.starts_at
                - timedelta(minutes=EARLY_CHECK_IN_TOLERANCE_MINUTES)
                <= current
                <= reservation.check_in_deadline_at
            )
        ):
            raise ReservationCheckInUnavailable()
        user_reference = reservation.user_reference
        affiliation_type = reservation.affiliation_type
        institutional_unit = reservation.institutional_unit
        planned_starts_at = reservation.starts_at
        planned_ends_at = reservation.ends_at
        exit_deadline_at = reservation.exit_deadline_at
    else:
        try:
            planned_starts_at = current
            validate_immediate_planned_end(
                starts_at=planned_starts_at,
                planned_ends_at=planned_ends_at,
                operating_day=operating_day,
            )
        except ValueError:
            raise UsageSessionConflict(
                "O horário planejado de saída não está disponível."
            )
        exit_deadline_at = planned_ends_at + timedelta(
            minutes=LATE_CHECK_OUT_TOLERANCE_MINUTES
        )
    if computer.operational_state != Computer.OperationalState.AVAILABLE:
        raise UsageSessionConflict("O computador não está operacionalmente disponível.")
    if UseSession.objects.filter(
        user_reference=user_reference,
        status=UseSession.Status.ACTIVE,
    ).exists():
        raise UsageSessionConflict("O usuário já possui uma sessão ativa.")
    if ComputerAllocation.objects.filter(
        computer=computer,
        ended_at__isnull=True,
    ).exists():
        raise UsageSessionConflict("O computador já possui uma alocação ativa.")
    if reservation is None and _reservation_blocks_interval(
        computer_id=computer.pk,
        user_reference=user_reference,
        starts_at=planned_starts_at,
        ends_at=planned_ends_at,
    ):
        raise UsageSessionConflict("O intervalo conflita com uma reserva confirmada.")
    if _planned_allocation_blocks_interval(
        computer_id=computer.pk,
        starts_at=planned_starts_at,
        ends_at=planned_ends_at,
    ):
        raise UsageSessionConflict("O intervalo conflita com outra sessão planejada.")

    try:
        with transaction.atomic():
            session = UseSession.objects.create(
                user_reference=user_reference,
                affiliation_type=affiliation_type,
                institutional_unit=institutional_unit,
                reservation=reservation,
                started_at=current,
                planned_starts_at=planned_starts_at,
                planned_ends_at=planned_ends_at,
                exit_deadline_at=exit_deadline_at,
                start_shift=_shift_at(current),
                entry_recorded_by_profile=actor_profile,
            )
            ComputerAllocation.objects.create(
                session=session,
                computer=computer,
                sequence=1,
                started_at=current,
            )
            if reservation is not None:
                reservation.status = Reservation.Status.USED
                reservation.save(update_fields=["status", "updated_at"])
            return session
    except IntegrityError as error:
        raise UsageSessionConflict() from error


def switch_computer(
    *,
    session_id: int,
    computer_id: int,
    actor_profile: str,
    actor_reference: str,
    reason: str = "",
    now: datetime | None = None,
) -> UseSession:
    current = now or timezone.now()
    source_computer_id = (
        ComputerAllocation.objects.filter(
            session_id=session_id,
            ended_at__isnull=True,
        )
        .values_list("computer_id", flat=True)
        .first()
    )
    computer_ids = {computer_id}
    if source_computer_id is not None:
        computer_ids.add(source_computer_id)
    for target_id in sorted(computer_ids):
        reconcile_computer_deadlines(target_id, current)
    return _switch_computer(
        session_id=session_id,
        computer_id=computer_id,
        actor_profile=actor_profile,
        actor_reference=actor_reference,
        reason=reason,
        current=current,
    )


@transaction.atomic
def _switch_computer(
    *,
    session_id: int,
    computer_id: int,
    actor_profile: str,
    actor_reference: str,
    reason: str,
    current: datetime,
) -> UseSession:
    session_preview = UseSession.objects.only("user_reference").get(pk=session_id)
    lock_user_reference(session_preview.user_reference)
    source_computer_id = (
        ComputerAllocation.objects.filter(
            session_id=session_id,
            ended_at__isnull=True,
        )
        .values_list("computer_id", flat=True)
        .first()
    )
    computer_ids = {computer_id}
    if source_computer_id is not None:
        computer_ids.add(source_computer_id)
    computers = {
        computer.pk: computer
        for computer in Computer.objects.select_for_update()
        .filter(pk__in=sorted(computer_ids))
        .order_by("pk")
    }
    session = _get_active_session(
        session_id=session_id,
        actor_profile=actor_profile,
        actor_reference=actor_reference,
    )
    allocation = session.allocations.select_for_update().get(ended_at__isnull=True)
    if current < allocation.started_at:
        raise UsageSessionConflict("A troca não pode anteceder a alocação atual.")
    if current >= session.planned_ends_at:
        raise UsageSessionConflict("A troca exige tempo planejado restante.")
    destination = computers[computer_id]
    if (
        destination.pk == allocation.computer_id
        or destination.operational_state != Computer.OperationalState.AVAILABLE
        or ComputerAllocation.objects.filter(
            computer=destination,
            ended_at__isnull=True,
        )
        .exclude(pk=allocation.pk)
        .exists()
        or _reservation_blocks_interval(
            computer_id=destination.pk,
            user_reference=session.user_reference,
            starts_at=current,
            ends_at=session.planned_ends_at,
        )
        or _planned_allocation_blocks_interval(
            computer_id=destination.pk,
            starts_at=current,
            ends_at=session.planned_ends_at,
        )
    ):
        raise UsageSessionConflict("O computador de destino não está disponível.")

    allocation.ended_at = current
    allocation.end_reason = ComputerAllocation.EndReason.SWITCH
    allocation.switch_reason = reason.strip()
    allocation.save(
        update_fields=["ended_at", "end_reason", "switch_reason", "updated_at"]
    )
    ComputerAllocation.objects.create(
        session=session,
        computer=destination,
        sequence=allocation.sequence + 1,
        started_at=current,
    )
    return session


@transaction.atomic
def finish_usage_session(
    *,
    session_id: int,
    actor_profile: str,
    actor_reference: str,
    reason: str = "",
    now: datetime | None = None,
) -> UseSession:
    current = now or timezone.now()
    session = _get_active_session(
        session_id=session_id,
        actor_profile=actor_profile,
        actor_reference=actor_reference,
    )
    if current > session.exit_deadline_at:
        expire_locked_session(session)
        return session
    is_owner = actor_reference == session.user_reference
    finish_reason = reason.strip()
    if not is_owner and not finish_reason:
        raise UsageSessionReasonRequired()

    allocation = session.allocations.select_for_update().get(ended_at__isnull=True)
    if current < allocation.started_at:
        raise UsageSessionConflict("A saída não pode anteceder a alocação atual.")
    allocation.ended_at = current
    allocation.end_reason = ComputerAllocation.EndReason.SESSION_FINISHED
    allocation.save(update_fields=["ended_at", "end_reason", "updated_at"])

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
    if not is_owner:
        AuditEvent.objects.create(
            actor_profile=actor_profile,
            action="USAGE_SESSION_FINISHED",
            entity_type="UseSession",
            entity_id=str(session.pk),
            old_values={"status": UseSession.Status.ACTIVE},
            new_values={
                "status": UseSession.Status.FINISHED,
                "ended_at": current.isoformat(),
            },
            reason=finish_reason,
        )
    return session
