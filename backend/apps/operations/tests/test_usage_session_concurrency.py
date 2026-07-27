from datetime import datetime, time, timedelta
from threading import Barrier, Thread

from django.db import close_old_connections, connections
from django.test import TransactionTestCase
from django.utils import timezone

from apps.computers.models import Computer
from apps.configuration.models import BookingPolicy, Shift
from apps.core.api.errors import UsageSessionConflict
from apps.operations.models import ComputerAllocation, UseSession
from apps.operations.services import start_usage_session


class UsageSessionConcurrencyTest(TransactionTestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.current = timezone.make_aware(
            datetime.combine(self.today, time(8, 0)),
            timezone.get_current_timezone(),
        )
        self.computer = Computer.objects.create(code="PC-01")
        Shift.objects.create(
            name="1º Turno",
            start_time=time(7, 0),
            end_time=time(13, 0),
            valid_from=self.today - timedelta(days=1),
        )
        BookingPolicy.objects.create(
            valid_from=self.today - timedelta(days=1),
            is_active=True,
        )

    def test_concurrent_entries_do_not_allocate_same_computer_twice(self):
        barrier = Barrier(2)
        results = []

        def enter(user_reference):
            close_old_connections()
            try:
                barrier.wait()
                start_usage_session(
                    computer_id=self.computer.pk,
                    actor_profile="ROOM_USER",
                    actor_reference=user_reference,
                    affiliation_type="STUDENT",
                    institutional_unit="Sistemas de Informação",
                    now=self.current,
                )
                results.append("created")
            except UsageSessionConflict:
                results.append("conflict")
            finally:
                connections.close_all()

        first = Thread(target=enter, args=("aluno-si-001",))
        second = Thread(target=enter, args=("aluno-si-002",))
        first.start()
        second.start()
        first.join()
        second.join()

        self.assertCountEqual(results, ["created", "conflict"])
        self.assertEqual(UseSession.objects.filter(status="ACTIVE").count(), 1)
        self.assertEqual(
            ComputerAllocation.objects.filter(ended_at__isnull=True).count(),
            1,
        )
