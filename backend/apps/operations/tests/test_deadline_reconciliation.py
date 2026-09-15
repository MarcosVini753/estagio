from datetime import datetime, time, timedelta

from django.test import TestCase
from django.utils import timezone

from apps.computers.models import Computer
from apps.configuration.models import BookingPolicy, OperatingSchedule, Weekday
from apps.configuration.tests.factories import create_operating_schedule
from apps.operations.availability import get_computers_availability
from apps.operations.models import ComputerAllocation, Reservation, UseSession
from apps.operations.services import start_usage_session
from apps.operations.services.deadlines import (
    ReconcileScope,
    cancel_overdue_reservations,
    expire_overdue_sessions,
    reconcile_deadlines,
)

from .factories import create_reservation, create_use_session


class ReconcileBoundaryTest(TestCase):
    def setUp(self):
        self.computer = Computer.objects.create(code="PC-01")

    def occupy(self, *, user_reference, deadline):
        session = create_use_session(
            user_reference=user_reference,
            started_at=deadline - timedelta(minutes=30),
            planned_starts_at=deadline - timedelta(minutes=30),
            planned_ends_at=deadline - timedelta(minutes=3),
            exit_deadline_at=deadline,
            entry_recorded_by_profile="ROOM_USER",
        )
        ComputerAllocation.objects.create(
            session=session,
            computer=self.computer,
            sequence=1,
            started_at=session.started_at,
        )
        return session

    def test_session_expires_exactly_at_its_exit_deadline(self):
        deadline = timezone.now()
        session = self.occupy(user_reference="aluno-limite", deadline=deadline)

        expire_overdue_sessions(timezone.now())

        session.refresh_from_db()
        self.assertEqual(session.status, UseSession.Status.FINISHED)
        self.assertEqual(session.ended_at, deadline)
        self.assertEqual(session.allocations.get().ended_at, deadline)

    def test_reservation_survives_the_exact_check_in_deadline(self):
        deadline = timezone.now()
        reservation = create_reservation(
            user_reference="aluno-limite",
            computer=self.computer,
            starts_at=deadline - timedelta(minutes=3),
            ends_at=deadline + timedelta(hours=1),
            check_in_deadline_at=deadline,
            created_by_profile="ROOM_USER",
        )

        cancel_overdue_reservations(deadline)

        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.CONFIRMED)

    def test_reservation_records_the_processing_instant_when_cancelled(self):
        deadline = timezone.now()
        reservation = create_reservation(
            user_reference="aluno-limite",
            computer=self.computer,
            starts_at=deadline - timedelta(minutes=3),
            ends_at=deadline + timedelta(hours=1),
            check_in_deadline_at=deadline,
            created_by_profile="ROOM_USER",
        )
        processed_at = deadline + timedelta(seconds=1)

        cancel_overdue_reservations(processed_at)

        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.CANCELLED)
        self.assertEqual(reservation.cancelled_at, processed_at)


class ReconcileScopeTest(TestCase):
    def setUp(self):
        self.computer = Computer.objects.create(code="PC-01")
        self.other_computer = Computer.objects.create(code="PC-02")

    def occupy(self, *, user_reference, computer):
        deadline = timezone.now() - timedelta(minutes=5)
        session = create_use_session(
            user_reference=user_reference,
            started_at=deadline - timedelta(minutes=30),
            planned_starts_at=deadline - timedelta(minutes=30),
            planned_ends_at=deadline - timedelta(minutes=3),
            exit_deadline_at=deadline,
            entry_recorded_by_profile="ROOM_USER",
        )
        ComputerAllocation.objects.create(
            session=session,
            computer=computer,
            sequence=1,
            started_at=session.started_at,
        )
        return session

    def test_user_scope_leaves_other_users_untouched(self):
        mine = self.occupy(user_reference="aluno-a", computer=self.computer)
        other = self.occupy(user_reference="aluno-b", computer=self.other_computer)

        reconcile_deadlines(
            now=timezone.now(),
            scope=ReconcileScope(user_references=("aluno-a",)),
        )

        mine.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(mine.status, UseSession.Status.FINISHED)
        self.assertEqual(other.status, UseSession.Status.ACTIVE)

    def test_computer_scope_leaves_other_computers_untouched(self):
        mine = self.occupy(user_reference="aluno-a", computer=self.computer)
        other = self.occupy(user_reference="aluno-b", computer=self.other_computer)

        reconcile_deadlines(
            now=timezone.now(),
            scope=ReconcileScope(computer_ids=(self.computer.pk,)),
        )

        mine.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(mine.status, UseSession.Status.FINISHED)
        self.assertEqual(other.status, UseSession.Status.ACTIVE)


class AvailabilityReconciliationTest(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.now = self.aware(10)
        self.computer = Computer.objects.create(code="PC-01")
        OperatingSchedule.objects.all().delete()
        create_operating_schedule(
            valid_from=self.today - timedelta(days=1),
            weekday_windows={
                weekday: [(time(7), time(22))] for weekday in Weekday.values
            },
        )
        BookingPolicy.objects.create(valid_from=self.today - timedelta(days=1))

    def aware(self, hour, minute=0):
        return timezone.make_aware(
            datetime.combine(self.today, time(hour, minute)),
            timezone.get_current_timezone(),
        )

    def test_availability_reconciles_an_expired_session_before_responding(self):
        session = create_use_session(
            user_reference="aluno-vencido",
            started_at=self.aware(9),
            planned_starts_at=self.aware(9),
            planned_ends_at=self.aware(9, 30),
            exit_deadline_at=self.aware(9, 33),
            entry_recorded_by_profile="ROOM_USER",
        )
        ComputerAllocation.objects.create(
            session=session,
            computer=self.computer,
            sequence=1,
            started_at=session.started_at,
        )

        summary, _ = get_computers_availability(
            target_date=self.today,
            computers=[self.computer],
            user_reference="aluno-vencido",
            now=self.now,
        )

        session.refresh_from_db()
        self.assertEqual(session.status, UseSession.Status.FINISHED)
        self.assertEqual(session.ended_at, self.aware(9, 33))
        self.assertEqual(session.allocations.get().ended_at, self.aware(9, 33))
        self.assertEqual(summary["computers"][0]["effective_status_now"], "AVAILABLE")

        started = start_usage_session(
            computer_id=self.computer.pk,
            planned_ends_at=self.aware(10, 15),
            actor_profile="ROOM_USER",
            actor_reference="aluno-vencido",
            affiliation_type="STUDENT",
            institutional_unit="Sistemas de Informação",
            now=self.now,
        )

        self.assertEqual(started.status, UseSession.Status.ACTIVE)
        self.assertEqual(
            ComputerAllocation.objects.filter(computer=self.computer).count(),
            2,
        )
