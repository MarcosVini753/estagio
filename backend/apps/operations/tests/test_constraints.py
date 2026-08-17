from datetime import timedelta

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.computers.models import Computer
from apps.operations.models import ComputerAllocation, Reservation

from .factories import create_reservation, create_use_session


class OperationConstraintTest(TestCase):
    def setUp(self):
        self.computer = Computer.objects.create(code="PC-01")

    def test_user_cannot_have_two_active_sessions(self):
        create_use_session(
            user_reference="demo-user", entry_recorded_by_profile="ROOM_USER"
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            create_use_session(
                user_reference="demo-user", entry_recorded_by_profile="ROOM_USER"
            )

    def test_computer_cannot_have_two_active_allocations(self):
        first_session = create_use_session(
            user_reference="user-1", entry_recorded_by_profile="ROOM_USER"
        )
        second_session = create_use_session(
            user_reference="user-2", entry_recorded_by_profile="ROOM_USER"
        )
        ComputerAllocation.objects.create(
            session=first_session, computer=self.computer, sequence=1
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            ComputerAllocation.objects.create(
                session=second_session, computer=self.computer, sequence=1
            )

    def test_historical_snapshots_default_to_not_informed(self):
        reservation = create_reservation(
            user_reference="legacy-user",
            computer=self.computer,
            starts_at="2026-01-01T08:00:00-05:00",
            ends_at="2026-01-01T09:00:00-05:00",
            created_by_profile="ROOM_USER",
        )
        session = create_use_session(
            user_reference="legacy-user",
            entry_recorded_by_profile="ROOM_USER",
        )

        self.assertEqual(reservation.affiliation_type, "NOT_INFORMED")
        self.assertEqual(reservation.institutional_unit, "")
        self.assertEqual(session.affiliation_type, "NOT_INFORMED")

    def test_confirmed_reservations_cannot_overlap_for_computer_or_user(self):
        create_reservation(
            user_reference="user-1",
            computer=self.computer,
            starts_at="2026-08-01T08:00:00-05:00",
            ends_at="2026-08-01T09:00:00-05:00",
            created_by_profile="ROOM_USER",
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            create_reservation(
                user_reference="user-2",
                computer=self.computer,
                starts_at="2026-08-01T08:30:00-05:00",
                ends_at="2026-08-01T09:30:00-05:00",
                created_by_profile="ROOM_USER",
            )

        other_computer = Computer.objects.create(code="PC-02")
        with self.assertRaises(IntegrityError), transaction.atomic():
            create_reservation(
                user_reference="user-1",
                computer=other_computer,
                starts_at="2026-08-01T08:30:00-05:00",
                ends_at="2026-08-01T09:30:00-05:00",
                created_by_profile="ROOM_USER",
            )

    def test_adjacent_and_cancelled_reservations_do_not_overlap(self):
        create_reservation(
            user_reference="user-1",
            computer=self.computer,
            starts_at="2026-08-01T08:00:00-05:00",
            ends_at="2026-08-01T09:00:00-05:00",
            created_by_profile="ROOM_USER",
        )
        create_reservation(
            user_reference="user-2",
            computer=self.computer,
            starts_at="2026-08-01T09:00:00-05:00",
            ends_at="2026-08-01T10:00:00-05:00",
            created_by_profile="ROOM_USER",
        )
        create_reservation(
            user_reference="user-3",
            computer=self.computer,
            starts_at="2026-08-01T08:30:00-05:00",
            ends_at="2026-08-01T09:30:00-05:00",
            status=Reservation.Status.CANCELLED,
            created_by_profile="ROOM_USER",
        )

    def test_reservation_deadlines_cannot_precede_their_reference_times(self):
        starts_at = timezone.now() + timedelta(days=1)
        ends_at = starts_at + timedelta(hours=1)

        with self.assertRaises(IntegrityError), transaction.atomic():
            create_reservation(
                user_reference="invalid-check-in",
                computer=self.computer,
                starts_at=starts_at,
                ends_at=ends_at,
                check_in_deadline_at=starts_at - timedelta(seconds=1),
                created_by_profile="ROOM_USER",
            )

        with self.assertRaises(IntegrityError), transaction.atomic():
            create_reservation(
                user_reference="invalid-exit",
                computer=self.computer,
                starts_at=starts_at,
                ends_at=ends_at,
                exit_deadline_at=ends_at - timedelta(seconds=1),
                created_by_profile="ROOM_USER",
            )

    def test_session_enforces_planned_interval_and_early_check_in_limit(self):
        starts_at = timezone.now()

        with self.assertRaises(IntegrityError), transaction.atomic():
            create_use_session(
                user_reference="invalid-interval",
                started_at=starts_at,
                planned_starts_at=starts_at,
                planned_ends_at=starts_at,
                exit_deadline_at=starts_at + timedelta(minutes=3),
                entry_recorded_by_profile="ROOM_USER",
            )

        reservation = create_reservation(
            user_reference="allowed-early-entry",
            computer=self.computer,
            starts_at=starts_at + timedelta(minutes=3),
            ends_at=starts_at + timedelta(minutes=18),
            created_by_profile="ROOM_USER",
        )
        allowed_early_session = create_use_session(
            user_reference="allowed-early-entry",
            reservation=reservation,
            started_at=starts_at,
            planned_starts_at=reservation.starts_at,
            planned_ends_at=reservation.ends_at,
            exit_deadline_at=reservation.exit_deadline_at,
            entry_recorded_by_profile="ROOM_USER",
        )

        self.assertEqual(allowed_early_session.started_at, starts_at)

        with self.assertRaises(IntegrityError), transaction.atomic():
            create_use_session(
                user_reference="immediate-entry-before-start",
                started_at=starts_at,
                planned_starts_at=starts_at + timedelta(minutes=3),
                planned_ends_at=starts_at + timedelta(minutes=18),
                exit_deadline_at=starts_at + timedelta(minutes=21),
                entry_recorded_by_profile="ROOM_USER",
            )
