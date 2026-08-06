from datetime import datetime, time, timedelta
from threading import Barrier, Thread

from django.db import close_old_connections, connections
from django.test import TransactionTestCase
from django.utils import timezone

from apps.computers.models import Computer
from apps.configuration.models import BookingPolicy, OperatingSchedule, Shift, Weekday
from apps.configuration.tests.factories import create_operating_schedule
from apps.core.api.errors import ReservationConflict
from apps.operations.models import Reservation
from apps.operations.services import create_reservation


class ReservationConcurrencyTest(TransactionTestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.tomorrow = self.today + timedelta(days=1)
        self.computer = Computer.objects.create(code="PC-01")
        Shift.objects.create(
            name="Manhã",
            start_time=time(7, 0),
            end_time=time(10, 0),
            valid_from=self.today - timedelta(days=1),
        )
        OperatingSchedule.objects.all().delete()
        create_operating_schedule(
            valid_from=self.today - timedelta(days=1),
            weekday_windows={
                weekday: [(time(7), time(10))] for weekday in Weekday.values
            },
        )
        BookingPolicy.objects.create(
            max_future_reservations_per_user=2,
            valid_from=self.today - timedelta(days=1),
            is_active=True,
        )

    def test_concurrent_attempts_do_not_confirm_two_conflicting_reservations(self):
        starts_at = timezone.make_aware(
            datetime.combine(self.tomorrow, time(8, 0)),
            timezone.get_current_timezone(),
        )
        barrier = Barrier(2)
        results = []

        def reserve():
            close_old_connections()
            try:
                barrier.wait()
                create_reservation(
                    computer_id=self.computer.pk,
                    starts_at=starts_at,
                    slot_count=4,
                    user_reference="aluno-si-001",
                    affiliation_type="STUDENT",
                    institutional_unit="Sistemas de Informação",
                    created_by_profile="ROOM_USER",
                )
                results.append("created")
            except ReservationConflict:
                results.append("conflict")
            finally:
                connections.close_all()

        first = Thread(target=reserve)
        second = Thread(target=reserve)
        first.start()
        second.start()
        first.join()
        second.join()

        self.assertCountEqual(results, ["created", "conflict"])
        self.assertEqual(
            Reservation.objects.filter(status=Reservation.Status.CONFIRMED).count(),
            1,
        )
