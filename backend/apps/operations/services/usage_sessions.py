from datetime import datetime, timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.computers.models import Computer
from apps.configuration.calendar import (
    is_open_at,
    lock_operating_date,
    resolve_operating_day,
)
from apps.configuration.selectors import (
    get_booking_policy_for_date,
    get_shifts_for_date,
)
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
from apps.operations.services.reservations import lock_user_reference

OPERATIONAL_PROFILES = {
    DemoProfile.INTERN,
    DemoProfile.LIBRARY_SUPERVISOR,
    DemoProfile.SYSTEM_ADMIN,
}


def _room_is_open(current: datetime) -> bool:
    return is_open_at(
        resolve_operating_day(timezone.localdate(current)),
        current,
    )


def _shift_at(current: datetime):
    local = timezone.localtime(current)
    return (
        get_shifts_for_date(local.date())
        .filter(start_time__lte=local.time(), end_time__gt=local.time())
        .first()
    )


def _reservation_blocks(
    *, computer_id: int, user_reference: str, current: datetime
) -> bool:
    return (
        Reservation.objects.filter(
            computer_id=computer_id,
            status=Reservation.Status.CONFIRMED,
            starts_at__lte=current,
            ends_at__gt=current,
        )
        .exclude(user_reference=user_reference)
        .exists()
    )


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


@transaction.atomic
def start_usage_session(
    *,
    computer_id: int,
    actor_profile: str,
    actor_reference: str,
    reservation_id: int | None = None,
    user_reference: str | None = None,
    affiliation_type: str | None = None,
    institutional_unit: str | None = None,
    now: datetime | None = None,
) -> UseSession:
    current = now or timezone.now()
    lock_operating_date(timezone.localdate(current))
    reservation = None

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
    if not _room_is_open(current):
        raise RoomClosed()

    computer = Computer.objects.select_for_update().get(pk=computer_id)
    lock_user_reference(user_reference)
    if reservation_id is not None:
        reservation = Reservation.objects.select_for_update().get(pk=reservation_id)
        policy = get_booking_policy_for_date(timezone.localdate(reservation.starts_at))
        if policy is None:
            raise ReservationCheckInUnavailable()
        tolerance = timedelta(minutes=policy.check_in_tolerance_minutes)
        latest_entry = min(reservation.starts_at + tolerance, reservation.ends_at)
        if (
            reservation.status != Reservation.Status.CONFIRMED
            or reservation.computer_id != computer_id
            or (
                actor_profile == DemoProfile.ROOM_USER
                and actor_reference != reservation.user_reference
            )
            or not reservation.starts_at - tolerance <= current <= latest_entry
        ):
            raise ReservationCheckInUnavailable()
        user_reference = reservation.user_reference
        affiliation_type = reservation.affiliation_type
        institutional_unit = reservation.institutional_unit
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
    if reservation is None and _reservation_blocks(
        computer_id=computer.pk,
        user_reference=user_reference,
        current=current,
    ):
        raise UsageSessionConflict("O computador está reservado para outro usuário.")

    try:
        with transaction.atomic():
            session = UseSession.objects.create(
                user_reference=user_reference,
                affiliation_type=affiliation_type,
                institutional_unit=institutional_unit,
                reservation=reservation,
                started_at=current,
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


@transaction.atomic
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
    session = _get_active_session(
        session_id=session_id,
        actor_profile=actor_profile,
        actor_reference=actor_reference,
    )
    allocation = session.allocations.select_for_update().get(ended_at__isnull=True)
    if current < allocation.started_at:
        raise UsageSessionConflict("A troca não pode anteceder a alocação atual.")
    computers = {
        computer.pk: computer
        for computer in Computer.objects.select_for_update()
        .filter(pk__in=sorted({allocation.computer_id, computer_id}))
        .order_by("pk")
    }
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
        or _reservation_blocks(
            computer_id=destination.pk,
            user_reference=session.user_reference,
            current=current,
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
