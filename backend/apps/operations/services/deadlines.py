from datetime import datetime

from django.db import transaction

from apps.core.enums import DemoProfile
from apps.operations.models import ComputerAllocation, Reservation, UseSession


def expire_locked_session(session: UseSession) -> bool:
    if session.status != UseSession.Status.ACTIVE:
        return False
    allocation = session.allocations.select_for_update().get(ended_at__isnull=True)
    allocation.ended_at = session.exit_deadline_at
    allocation.end_reason = ComputerAllocation.EndReason.TIME_LIMIT_REACHED
    allocation.save(update_fields=["ended_at", "end_reason", "updated_at"])

    session.ended_at = session.exit_deadline_at
    session.status = UseSession.Status.FINISHED
    session.exit_recorded_by_profile = DemoProfile.SYSTEM_ADMIN
    session.save(
        update_fields=[
            "ended_at",
            "status",
            "exit_recorded_by_profile",
            "updated_at",
        ]
    )
    return True


@transaction.atomic
def expire_overdue_sessions(now: datetime) -> int:
    sessions = list(
        UseSession.objects.select_for_update()
        .filter(
            status=UseSession.Status.ACTIVE,
            exit_deadline_at__lte=now,
        )
        .order_by("pk")
    )
    return sum(expire_locked_session(session) for session in sessions)


@transaction.atomic
def mark_overdue_reservations_as_no_show(now: datetime) -> int:
    reservations = list(
        Reservation.objects.select_for_update()
        .filter(
            status=Reservation.Status.CONFIRMED,
            check_in_deadline_at__lt=now,
        )
        .order_by("pk")
    )
    for reservation in reservations:
        reservation.status = Reservation.Status.NO_SHOW
        reservation.no_show_at = now
        reservation.save(update_fields=["status", "no_show_at", "updated_at"])
    return len(reservations)


@transaction.atomic
def reconcile_computer_deadlines(computer_id: int, now: datetime) -> tuple[int, int]:
    active_session_ids = ComputerAllocation.objects.filter(
        computer_id=computer_id,
        ended_at__isnull=True,
    ).values_list("session_id", flat=True)
    sessions = list(
        UseSession.objects.select_for_update()
        .filter(
            pk__in=active_session_ids,
            status=UseSession.Status.ACTIVE,
            exit_deadline_at__lte=now,
        )
        .order_by("pk")
    )
    expired_sessions = sum(expire_locked_session(session) for session in sessions)

    reservations = list(
        Reservation.objects.select_for_update()
        .filter(
            computer_id=computer_id,
            status=Reservation.Status.CONFIRMED,
            check_in_deadline_at__lt=now,
        )
        .order_by("pk")
    )
    for reservation in reservations:
        reservation.status = Reservation.Status.NO_SHOW
        reservation.no_show_at = now
        reservation.save(update_fields=["status", "no_show_at", "updated_at"])
    return expired_sessions, len(reservations)
