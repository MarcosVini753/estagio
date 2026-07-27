from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.computers.models import Computer
from apps.operations.models import ComputerAllocation, Reservation, UseSession


class OperationConstraintTest(TestCase):
    def setUp(self):
        self.computer = Computer.objects.create(code="PC-01")

    def test_user_cannot_have_two_active_sessions(self):
        UseSession.objects.create(
            user_reference="demo-user", entry_recorded_by_profile="ROOM_USER"
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            UseSession.objects.create(
                user_reference="demo-user", entry_recorded_by_profile="ROOM_USER"
            )

    def test_computer_cannot_have_two_active_allocations(self):
        first_session = UseSession.objects.create(
            user_reference="user-1", entry_recorded_by_profile="ROOM_USER"
        )
        second_session = UseSession.objects.create(
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
        reservation = Reservation.objects.create(
            user_reference="legacy-user",
            computer=self.computer,
            starts_at="2026-01-01T08:00:00-05:00",
            ends_at="2026-01-01T09:00:00-05:00",
            created_by_profile="ROOM_USER",
        )
        session = UseSession.objects.create(
            user_reference="legacy-user",
            entry_recorded_by_profile="ROOM_USER",
        )

        self.assertEqual(reservation.affiliation_type, "NOT_INFORMED")
        self.assertEqual(reservation.institutional_unit, "")
        self.assertEqual(session.affiliation_type, "NOT_INFORMED")

    def test_confirmed_reservations_cannot_overlap_for_computer_or_user(self):
        Reservation.objects.create(
            user_reference="user-1",
            computer=self.computer,
            starts_at="2026-08-01T08:00:00-05:00",
            ends_at="2026-08-01T09:00:00-05:00",
            created_by_profile="ROOM_USER",
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            Reservation.objects.create(
                user_reference="user-2",
                computer=self.computer,
                starts_at="2026-08-01T08:30:00-05:00",
                ends_at="2026-08-01T09:30:00-05:00",
                created_by_profile="ROOM_USER",
            )

        other_computer = Computer.objects.create(code="PC-02")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Reservation.objects.create(
                user_reference="user-1",
                computer=other_computer,
                starts_at="2026-08-01T08:30:00-05:00",
                ends_at="2026-08-01T09:30:00-05:00",
                created_by_profile="ROOM_USER",
            )
