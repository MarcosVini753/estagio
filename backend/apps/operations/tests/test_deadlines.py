from datetime import datetime, time
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.computers.models import Computer
from apps.operations.models import ComputerAllocation, Reservation, UseSession
from apps.operations.services.deadlines import (
    expire_overdue_sessions,
    mark_overdue_reservations_as_no_show,
)

from .factories import create_reservation, create_use_session


class OperationalDeadlineTest(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.computer = Computer.objects.create(code="PC-01")

    def aware(self, value):
        return timezone.make_aware(
            datetime.combine(self.today, value),
            timezone.get_current_timezone(),
        )

    def create_active_session(self):
        session = create_use_session(
            user_reference="active-user",
            started_at=self.aware(time(8)),
            planned_ends_at=self.aware(time(9)),
            exit_deadline_at=self.aware(time(9, 3)),
            entry_recorded_by_profile="ROOM_USER",
        )
        allocation = ComputerAllocation.objects.create(
            session=session,
            computer=self.computer,
            sequence=1,
            started_at=self.aware(time(8)),
        )
        return session, allocation

    def test_reservation_becomes_no_show_only_after_check_in_deadline(self):
        reservation = create_reservation(
            user_reference="reserved-user",
            computer=self.computer,
            starts_at=self.aware(time(9)),
            ends_at=self.aware(time(10)),
            created_by_profile="ROOM_USER",
        )

        at_deadline = mark_overdue_reservations_as_no_show(self.aware(time(9, 3)))
        after_deadline = mark_overdue_reservations_as_no_show(self.aware(time(9, 3, 1)))

        self.assertEqual(at_deadline, 0)
        self.assertEqual(after_deadline, 1)
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.NO_SHOW)
        self.assertEqual(reservation.no_show_at, self.aware(time(9, 3, 1)))

    def test_expired_session_is_closed_at_deadline(self):
        session, allocation = self.create_active_session()

        expired = expire_overdue_sessions(self.aware(time(9, 3)))

        self.assertEqual(expired, 1)
        session.refresh_from_db()
        allocation.refresh_from_db()
        self.assertEqual(session.status, UseSession.Status.FINISHED)
        self.assertEqual(session.ended_at, self.aware(time(9, 3)))
        self.assertEqual(session.exit_recorded_by_profile, "SYSTEM_ADMIN")
        self.assertEqual(allocation.ended_at, self.aware(time(9, 3)))
        self.assertEqual(
            allocation.end_reason,
            ComputerAllocation.EndReason.TIME_LIMIT_REACHED,
        )

    def test_management_command_reconciles_sessions_and_no_shows(self):
        session, allocation = self.create_active_session()
        reservation = create_reservation(
            user_reference="reserved-user",
            computer=self.computer,
            starts_at=self.aware(time(8)),
            ends_at=self.aware(time(9)),
            created_by_profile="ROOM_USER",
        )
        current = self.aware(time(9, 3, 1))
        output = StringIO()

        with patch(
            "apps.operations.management.commands."
            "reconcile_operational_deadlines.timezone.now",
            return_value=current,
        ):
            call_command("reconcile_operational_deadlines", stdout=output)

        session.refresh_from_db()
        allocation.refresh_from_db()
        reservation.refresh_from_db()
        self.assertEqual(session.ended_at, self.aware(time(9, 3)))
        self.assertEqual(
            allocation.end_reason,
            ComputerAllocation.EndReason.TIME_LIMIT_REACHED,
        )
        self.assertEqual(reservation.status, Reservation.Status.NO_SHOW)
        self.assertIn("1 sessão(ões) expirada(s)", output.getvalue())
        self.assertIn("1 reserva(s) sem comparecimento", output.getvalue())
