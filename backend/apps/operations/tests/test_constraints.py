from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.computers.models import Computer
from apps.operations.models import ComputerAllocation, UseSession


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
