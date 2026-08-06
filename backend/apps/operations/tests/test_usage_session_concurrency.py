from datetime import datetime, time, timedelta
from threading import Barrier, Thread

from django.db import close_old_connections, connections
from django.test import TransactionTestCase
from django.utils import timezone

from apps.computers.models import Computer
from apps.configuration.models import BookingPolicy, OperatingSchedule, Shift, Weekday
from apps.configuration.tests.factories import create_operating_schedule
from apps.core.api.errors import (
    ReservationConflict,
    ReservationUnavailable,
    UsageSessionConflict,
)
from apps.operations.models import ComputerAllocation, Reservation, UseSession
from apps.operations.services import (
    create_reservation,
    start_usage_session,
    switch_computer,
)

from .factories import create_use_session


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
        OperatingSchedule.objects.all().delete()
        create_operating_schedule(
            valid_from=self.today - timedelta(days=1),
            weekday_windows={
                weekday: [(time(7), time(13))] for weekday in Weekday.values
            },
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
                    slot_count=4,
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

    def test_reservation_and_immediate_entry_have_only_one_winner(self):
        barrier = Barrier(2)
        results = []
        reservation_start = self.current + timedelta(minutes=15)

        def reserve():
            close_old_connections()
            try:
                barrier.wait()
                create_reservation(
                    computer_id=self.computer.pk,
                    starts_at=reservation_start,
                    slot_count=3,
                    user_reference="reserved-user",
                    affiliation_type="STUDENT",
                    institutional_unit="Sistemas de Informação",
                    created_by_profile="ROOM_USER",
                    now=self.current,
                )
                results.append("reservation")
            except (ReservationConflict, ReservationUnavailable):
                results.append("conflict")
            finally:
                connections.close_all()

        def enter():
            close_old_connections()
            try:
                barrier.wait()
                start_usage_session(
                    computer_id=self.computer.pk,
                    slot_count=4,
                    actor_profile="ROOM_USER",
                    actor_reference="immediate-user",
                    affiliation_type="STUDENT",
                    institutional_unit="Sistemas de Informação",
                    now=self.current,
                )
                results.append("session")
            except UsageSessionConflict:
                results.append("conflict")
            finally:
                connections.close_all()

        reservation_thread = Thread(target=reserve)
        session_thread = Thread(target=enter)
        reservation_thread.start()
        session_thread.start()
        reservation_thread.join()
        session_thread.join()

        self.assertEqual(results.count("conflict"), 1)
        self.assertEqual(len(results), 2)
        self.assertEqual(
            Reservation.objects.filter(status=Reservation.Status.CONFIRMED).count()
            + UseSession.objects.filter(status=UseSession.Status.ACTIVE).count(),
            1,
        )

    def test_reservation_and_switch_have_only_one_winner(self):
        source = Computer.objects.create(code="PC-02")
        session = create_use_session(
            user_reference="switching-user",
            started_at=self.current,
            planned_ends_at=self.current + timedelta(hours=1),
            exit_deadline_at=self.current + timedelta(hours=1, minutes=3),
            entry_recorded_by_profile="ROOM_USER",
        )
        ComputerAllocation.objects.create(
            session=session,
            computer=source,
            sequence=1,
            started_at=self.current,
        )
        barrier = Barrier(2)
        results = []

        def reserve():
            close_old_connections()
            try:
                barrier.wait()
                create_reservation(
                    computer_id=self.computer.pk,
                    starts_at=self.current + timedelta(minutes=30),
                    slot_count=2,
                    user_reference="reserved-user",
                    affiliation_type="STUDENT",
                    institutional_unit="Sistemas de Informação",
                    created_by_profile="ROOM_USER",
                    now=self.current,
                )
                results.append("reservation")
            except (ReservationConflict, ReservationUnavailable):
                results.append("conflict")
            finally:
                connections.close_all()

        def switch():
            close_old_connections()
            try:
                barrier.wait()
                switch_computer(
                    session_id=session.pk,
                    computer_id=self.computer.pk,
                    actor_profile="ROOM_USER",
                    actor_reference="switching-user",
                    now=self.current + timedelta(minutes=15),
                )
                results.append("switch")
            except UsageSessionConflict:
                results.append("conflict")
            finally:
                connections.close_all()

        reservation_thread = Thread(target=reserve)
        switch_thread = Thread(target=switch)
        reservation_thread.start()
        switch_thread.start()
        reservation_thread.join()
        switch_thread.join()

        self.assertEqual(results.count("conflict"), 1)
        self.assertEqual(len(results), 2)
        destination_is_allocated = ComputerAllocation.objects.filter(
            computer=self.computer,
            ended_at__isnull=True,
        ).exists()
        destination_is_reserved = Reservation.objects.filter(
            computer=self.computer,
            status=Reservation.Status.CONFIRMED,
        ).exists()
        self.assertNotEqual(destination_is_allocated, destination_is_reserved)
