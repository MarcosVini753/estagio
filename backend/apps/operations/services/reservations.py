from datetime import datetime, timedelta

from django.db import IntegrityError, connection, transaction
from django.db.models import Q
from django.utils import timezone

from apps.computers.models import Computer
from apps.configuration.selectors import get_booking_policy_for_date
from apps.core.api.errors import (
    ConfigurationRequired,
    ReservationCancellationNotAllowed,
    ReservationCancellationUnavailable,
    ReservationConflict,
    ReservationLimitReached,
    ReservationSlotInvalid,
    ReservationUnavailable,
)
from apps.core.enums import DemoProfile
from apps.operations.availability import generate_slot_intervals, validate_target_date
from apps.operations.models import ComputerAllocation, Reservation


def _lock_user_reference(user_reference: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", [user_reference])


def _overlapping_allocations(
    *, computer_id: int, starts_at: datetime, ends_at: datetime
):
    return ComputerAllocation.objects.filter(
        computer_id=computer_id,
        started_at__lt=ends_at,
    ).filter(Q(ended_at__isnull=True) | Q(ended_at__gt=starts_at))


@transaction.atomic
def create_reservation(
    *,
    computer_id: int,
    starts_at: datetime,
    user_reference: str,
    affiliation_type: str,
    institutional_unit: str,
    created_by_profile: str,
    now: datetime | None = None,
) -> Reservation:
    current = now or timezone.now()
    target_date = timezone.localdate(starts_at)
    today = validate_target_date(target_date, now=current)
    _, _, slots = generate_slot_intervals(target_date)
    ends_at = next((end for start, end in slots if start == starts_at), None)

    if ends_at is None or (target_date == today and starts_at <= current):
        raise ReservationSlotInvalid()

    computer = Computer.objects.select_for_update().get(pk=computer_id)
    if computer.operational_state != Computer.OperationalState.AVAILABLE:
        raise ReservationUnavailable()

    _lock_user_reference(user_reference)
    if _overlapping_allocations(
        computer_id=computer.pk,
        starts_at=starts_at,
        ends_at=ends_at,
    ).exists():
        raise ReservationUnavailable()

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
            return Reservation.objects.create(
                user_reference=user_reference,
                affiliation_type=affiliation_type,
                institutional_unit=institutional_unit,
                computer=computer,
                starts_at=starts_at,
                ends_at=ends_at,
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
        DemoProfile.INTERN,
        DemoProfile.LIBRARY_SUPERVISOR,
        DemoProfile.SYSTEM_ADMIN,
    }
    if (
        actor_profile not in operational_profiles
        and actor_reference != reservation.user_reference
    ):
        raise ReservationCancellationNotAllowed()

    current = now or timezone.now()
    target_date = timezone.localdate(reservation.starts_at)
    policy = get_booking_policy_for_date(target_date)
    if policy is None:
        raise ConfigurationRequired(
            "Nenhuma política de reservas está ativa para a data da reserva."
        )
    cancellation_deadline = reservation.starts_at - timedelta(
        minutes=policy.cancellation_limit_minutes
    )
    if (
        reservation.status != Reservation.Status.CONFIRMED
        or current >= reservation.starts_at
        or current > cancellation_deadline
    ):
        raise ReservationCancellationUnavailable()

    reservation.status = Reservation.Status.CANCELLED
    reservation.cancelled_by_profile = actor_profile
    reservation.cancelled_at = current
    reservation.cancellation_reason = reason.strip()
    reservation.save(
        update_fields=[
            "status",
            "cancelled_by_profile",
            "cancelled_at",
            "cancellation_reason",
            "updated_at",
        ]
    )
    return reservation
