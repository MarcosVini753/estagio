from datetime import datetime, timedelta

from django.db import IntegrityError, connection, transaction
from django.db.models import Q
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.computers.models import Computer
from apps.configuration.calendar import lock_operating_date, resolve_operating_day
from apps.configuration.models import BookingPolicy
from apps.configuration.selectors import get_booking_policy_for_date
from apps.core.api.errors import (
    ReservationCancellationNotAllowed,
    ReservationCancellationReasonRequired,
    ReservationCancellationUnavailable,
    ReservationConflict,
    ReservationLimitReached,
    ReservationSlotInvalid,
    ReservationUnavailable,
)
from apps.core.enums import DemoProfile
from apps.operations.availability import validate_target_date
from apps.operations.models import ComputerAllocation, Reservation, UseSession
from apps.operations.rules import (
    LATE_CHECK_IN_TOLERANCE_MINUTES,
    LATE_CHECK_OUT_TOLERANCE_MINUTES,
)
from apps.operations.slotting import (
    calculate_interval,
    validate_interval_inside_operating_window,
    validate_reservation_slot_start,
)


def lock_user_reference(user_reference: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", [user_reference])


def _overlapping_allocations(
    *, computer_id: int, starts_at: datetime, ends_at: datetime
):
    return ComputerAllocation.objects.filter(
        computer_id=computer_id,
        ended_at__isnull=True,
        session__status=UseSession.Status.ACTIVE,
        session__planned_starts_at__lt=ends_at,
        session__planned_ends_at__gt=starts_at,
    )


@transaction.atomic
def create_reservation(
    *,
    computer_id: int,
    starts_at: datetime,
    slot_count: int,
    user_reference: str,
    affiliation_type: str,
    institutional_unit: str,
    created_by_profile: str,
    now: datetime | None = None,
) -> Reservation:
    current = now or timezone.now()
    target_date = timezone.localdate(starts_at)
    today = validate_target_date(target_date, now=current)
    lock_operating_date(target_date)
    operating_day = resolve_operating_day(target_date)
    try:
        ends_at = calculate_interval(starts_at, slot_count)
        validate_reservation_slot_start(starts_at, operating_day)
        validate_interval_inside_operating_window(starts_at, ends_at, operating_day)
    except ValueError as error:
        raise ReservationSlotInvalid() from error

    if target_date == today and starts_at <= current:
        raise ReservationSlotInvalid()

    lock_user_reference(user_reference)
    computer = Computer.objects.select_for_update().get(pk=computer_id)
    if computer.operational_state != Computer.OperationalState.AVAILABLE:
        raise ReservationUnavailable()

    if _overlapping_allocations(
        computer_id=computer.pk,
        starts_at=starts_at,
        ends_at=ends_at,
    ).exists():
        raise ReservationUnavailable()

    if (
        UseSession.objects.select_for_update()
        .filter(
            status=UseSession.Status.ACTIVE,
            user_reference=user_reference,
            planned_starts_at__lt=ends_at,
            planned_ends_at__gt=starts_at,
        )
        .exists()
    ):
        raise ReservationConflict()

    conflicts = Reservation.objects.select_for_update().filter(
        status=Reservation.Status.CONFIRMED,
        starts_at__lt=ends_at,
        ends_at__gt=starts_at,
    )
    if conflicts.filter(
        Q(computer=computer) | Q(user_reference=user_reference)
    ).exists():
        raise ReservationConflict()

    policy = get_booking_policy_for_date(target_date)
    if policy is None:
        raise ReservationSlotInvalid()
    policy = BookingPolicy.objects.select_for_update().get(pk=policy.pk)
    if (
        Reservation.objects.filter(
            user_reference=user_reference,
            status=Reservation.Status.CONFIRMED,
            starts_at__gte=current,
        ).count()
        >= policy.max_future_reservations_per_user
    ):
        raise ReservationLimitReached()

    try:
        with transaction.atomic():
            check_in_deadline_at = starts_at + timedelta(
                minutes=LATE_CHECK_IN_TOLERANCE_MINUTES
            )
            exit_deadline_at = ends_at + timedelta(
                minutes=LATE_CHECK_OUT_TOLERANCE_MINUTES
            )
            return Reservation.objects.create(
                user_reference=user_reference,
                affiliation_type=affiliation_type,
                institutional_unit=institutional_unit,
                computer=computer,
                booking_policy=policy,
                starts_at=starts_at,
                ends_at=ends_at,
                check_in_deadline_at=check_in_deadline_at,
                exit_deadline_at=exit_deadline_at,
                created_by_profile=created_by_profile,
            )
    except IntegrityError as error:
        raise ReservationConflict() from error


@transaction.atomic
def cancel_reservation(
    *,
    reservation_id: int,
    actor_profile: str,
    actor_reference: str,
    reason: str = "",
    now: datetime | None = None,
) -> Reservation:
    reservation = Reservation.objects.select_for_update().get(pk=reservation_id)
    operational_profiles = {
        DemoProfile.ROOM_MONITOR,
        DemoProfile.LIBRARY_SUPERVISOR,
        DemoProfile.SYSTEM_ADMIN,
    }
    is_owner = actor_reference == reservation.user_reference
    if actor_profile not in operational_profiles and not is_owner:
        raise ReservationCancellationNotAllowed()
    cancellation_reason = reason.strip()
    if not is_owner and not cancellation_reason:
        raise ReservationCancellationReasonRequired()

    current = now or timezone.now()
    policy = reservation.booking_policy
    cancellation_deadline = reservation.starts_at - timedelta(
        minutes=policy.cancellation_limit_minutes
    )
    if (
        reservation.status != Reservation.Status.CONFIRMED
        or current >= reservation.starts_at
        or current > cancellation_deadline
    ):
        raise ReservationCancellationUnavailable()

    return cancel_locked_reservation(
        reservation=reservation,
        actor_profile=actor_profile,
        reason=cancellation_reason,
        cancelled_at=current,
        create_audit_event=not is_owner,
    )


def cancel_locked_reservation(
    *,
    reservation: Reservation,
    actor_profile: str,
    reason: str,
    cancelled_at: datetime,
    create_audit_event: bool = True,
) -> Reservation:
    if reservation.status != Reservation.Status.CONFIRMED:
        return reservation

    cancellation_reason = reason.strip()
    reservation.status = Reservation.Status.CANCELLED
    reservation.cancelled_by_profile = actor_profile
    reservation.cancelled_at = cancelled_at
    reservation.cancellation_reason = cancellation_reason
    reservation.save(
        update_fields=[
            "status",
            "cancelled_by_profile",
            "cancelled_at",
            "cancellation_reason",
            "updated_at",
        ]
    )
    if create_audit_event:
        AuditEvent.objects.create(
            actor_profile=actor_profile,
            action="RESERVATION_CANCELLED",
            entity_type="Reservation",
            entity_id=str(reservation.pk),
            old_values={"status": Reservation.Status.CONFIRMED},
            new_values={
                "status": Reservation.Status.CANCELLED,
                "cancelled_at": cancelled_at.isoformat(),
            },
            reason=cancellation_reason,
        )
    return reservation


@transaction.atomic
def cancel_reservation_due_to_operational_change(
    *,
    reservation_id: int,
    actor_profile: str,
    reason: str,
    now: datetime | None = None,
) -> Reservation:
    reservation = Reservation.objects.select_for_update().get(pk=reservation_id)
    if reservation.status != Reservation.Status.CONFIRMED:
        return reservation

    return cancel_locked_reservation(
        reservation=reservation,
        actor_profile=actor_profile,
        reason=reason,
        cancelled_at=now or timezone.now(),
    )
