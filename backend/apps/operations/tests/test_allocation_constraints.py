from datetime import datetime, time

from django.db import IntegrityError, transaction
from django.test import TransactionTestCase
from django.utils import timezone

from apps.computers.models import Computer
from apps.operations.models import ComputerAllocation, UseSession

from .factories import create_use_session


class AllocationTemporalConstraintTest(TransactionTestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.computer = Computer.objects.create(code="PC-01")

    def aware(self, value):
        return timezone.make_aware(
            datetime.combine(self.today, value),
            timezone.get_current_timezone(),
        )

    def allocation(self, user_reference, starts_at, ends_at):
        session = create_use_session(
            user_reference=user_reference,
            started_at=starts_at,
            ended_at=ends_at,
            status=UseSession.Status.FINISHED,
            entry_recorded_by_profile="ROOM_USER",
        )
        return ComputerAllocation.objects.create(
            session=session,
            computer=self.computer,
            sequence=1,
            started_at=starts_at,
            ended_at=ends_at,
            end_reason=ComputerAllocation.EndReason.SESSION_FINISHED,
        )

    def test_historical_allocations_cannot_overlap_for_same_computer(self):
        self.allocation(
            "aluno-si-001",
            self.aware(time(8, 0)),
            self.aware(time(9, 0)),
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.allocation(
                "aluno-si-002",
                self.aware(time(8, 30)),
                self.aware(time(9, 30)),
            )

    def test_adjacent_historical_allocations_are_allowed(self):
        self.allocation(
            "aluno-si-001",
            self.aware(time(8, 0)),
            self.aware(time(9, 0)),
        )

        self.allocation(
            "aluno-si-002",
            self.aware(time(9, 0)),
            self.aware(time(10, 0)),
        )
