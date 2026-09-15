from dataclasses import dataclass
from datetime import datetime

from django.db import transaction
from django.db.models import QuerySet

from apps.core.enums import DemoProfile
from apps.operations.models import ComputerAllocation, Reservation, UseSession
from apps.operations.services.reservations import cancel_locked_reservation


@dataclass(frozen=True)
class ReconcileScope:
    """Restringe a reconciliação ao que a operação realmente observa.

    Leituras operacionais não precisam processar o histórico inteiro: apenas os
    computadores, referências de usuário ou período que a resposta consulta.
    """

    computer_ids: tuple[int, ...] | None = None
    user_references: tuple[str, ...] | None = None
    period: tuple[datetime, datetime] | None = None


@dataclass(frozen=True)
class ReconcileResult:
    expired_sessions: int = 0
    cancelled_reservations: int = 0


def _scope_sessions(queryset: QuerySet, scope: ReconcileScope | None) -> QuerySet:
    if scope is None:
        return queryset
    if scope.computer_ids is not None:
        # Somente sessões que ainda ocupam um dos computadores observados.
        session_ids = ComputerAllocation.objects.filter(
            computer_id__in=scope.computer_ids,
            ended_at__isnull=True,
        ).values("session_id")
        queryset = queryset.filter(pk__in=session_ids)
    if scope.user_references is not None:
        queryset = queryset.filter(user_reference__in=scope.user_references)
    if scope.period is not None:
        starts_at, ends_at = scope.period
        queryset = queryset.filter(
            planned_starts_at__gte=starts_at,
            planned_starts_at__lt=ends_at,
        )
    return queryset


def _scope_reservations(queryset: QuerySet, scope: ReconcileScope | None) -> QuerySet:
    if scope is None:
        return queryset
    if scope.computer_ids is not None:
        queryset = queryset.filter(computer_id__in=scope.computer_ids)
    if scope.user_references is not None:
        queryset = queryset.filter(user_reference__in=scope.user_references)
    if scope.period is not None:
        starts_at, ends_at = scope.period
        queryset = queryset.filter(starts_at__gte=starts_at, starts_at__lt=ends_at)
    return queryset


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
def expire_overdue_sessions(
    now: datetime,
    *,
    scope: ReconcileScope | None = None,
) -> int:
    sessions = list(
        _scope_sessions(
            UseSession.objects.select_for_update().filter(
                status=UseSession.Status.ACTIVE,
                exit_deadline_at__lte=now,
            ),
            scope,
        ).order_by("pk")
    )
    return sum(expire_locked_session(session) for session in sessions)


@transaction.atomic
def cancel_overdue_reservations(
    now: datetime,
    *,
    scope: ReconcileScope | None = None,
) -> int:
    reservations = list(
        _scope_reservations(
            Reservation.objects.select_for_update().filter(
                status=Reservation.Status.CONFIRMED,
                check_in_deadline_at__lt=now,
            ),
            scope,
        ).order_by("pk")
    )
    for reservation in reservations:
        cancel_locked_reservation(
            reservation=reservation,
            actor_profile=DemoProfile.SYSTEM_ADMIN,
            reason="Prazo de check-in expirado.",
            cancelled_at=now,
        )
    return len(reservations)


def reconcile_deadlines(
    *,
    now: datetime,
    scope: ReconcileScope | None = None,
) -> ReconcileResult:
    """Reconcilia prazos vencidos antes de uma leitura operacional.

    O instante de referência é recebido uma única vez para que a consulta
    seguinte observe exatamente o mesmo `now` usado aqui.
    """

    return ReconcileResult(
        expired_sessions=expire_overdue_sessions(now, scope=scope),
        cancelled_reservations=cancel_overdue_reservations(now, scope=scope),
    )


@transaction.atomic
def reconcile_computer_deadlines(computer_id: int, now: datetime) -> tuple[int, int]:
    result = reconcile_deadlines(
        now=now,
        scope=ReconcileScope(computer_ids=(computer_id,)),
    )
    return result.expired_sessions, result.cancelled_reservations
