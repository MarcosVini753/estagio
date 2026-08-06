from datetime import datetime, time, timedelta
from threading import Event, Thread
from unittest.mock import patch

from django.db import close_old_connections, connections
from django.test import TransactionTestCase
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.computers.models import Computer
from apps.configuration.models import BookingPolicy, OperatingSchedule, Weekday
from apps.configuration.services import create_operating_schedule
from apps.core.api.errors import ReservationSlotInvalid
from apps.operations.services import create_reservation

from .factories import create_operating_schedule as create_schedule_fixture


class CalendarChangeConcurrencyTest(TransactionTestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.tomorrow = self.today + timedelta(days=1)
        self.computer = Computer.objects.create(code="PC-CALENDAR-LOCK")
        OperatingSchedule.objects.all().delete()
        create_schedule_fixture(
            valid_from=self.today - timedelta(days=1),
            weekday_windows={
                weekday: [(time(7), time(10))] for weekday in Weekday.values
            },
        )
        BookingPolicy.objects.create(
            slot_duration_minutes=60,
            max_future_reservations_per_user=2,
            valid_from=self.today - timedelta(days=1),
            is_active=True,
        )

    def test_reservation_waits_for_calendar_change_and_uses_new_windows(self):
        audit_reached = Event()
        release_change = Event()
        reservation_started = Event()
        results = []
        original_audit_create = AuditEvent.objects.create
        days = [
            {
                "weekday": weekday,
                "is_open": True,
                "windows": [{"opens_at": time(7), "closes_at": time(8)}],
            }
            for weekday in Weekday.values
        ]

        def hold_before_commit(*args, **kwargs):
            audit_reached.set()
            release_change.wait(timeout=5)
            return original_audit_create(*args, **kwargs)

        def change_calendar():
            close_old_connections()
            try:
                with patch(
                    "apps.configuration.services.AuditEvent.objects.create",
                    side_effect=hold_before_commit,
                ):
                    create_operating_schedule(
                        name="Horário reduzido",
                        schedule_type=OperatingSchedule.ScheduleType.TEMPORARY,
                        valid_from=self.tomorrow,
                        valid_until=self.tomorrow,
                        reason="Teste de concorrência.",
                        days=days,
                        actor_profile="LIBRARY_SUPERVISOR",
                    )
                results.append("calendar_changed")
            finally:
                connections.close_all()

        def reserve():
            close_old_connections()
            try:
                reservation_started.set()
                create_reservation(
                    computer_id=self.computer.pk,
                    starts_at=timezone.make_aware(
                        datetime.combine(self.tomorrow, time(8)),
                        timezone.get_current_timezone(),
                    ),
                    user_reference="aluno-concorrente",
                    affiliation_type="STUDENT",
                    institutional_unit="Sistemas de Informação",
                    created_by_profile="ROOM_USER",
                )
                results.append("reservation_created")
            except ReservationSlotInvalid:
                results.append("reservation_rejected")
            finally:
                connections.close_all()

        change_thread = Thread(target=change_calendar)
        change_thread.start()
        self.assertTrue(audit_reached.wait(timeout=5))
        reservation_thread = Thread(target=reserve)
        reservation_thread.start()
        self.assertTrue(reservation_started.wait(timeout=5))
        reservation_thread.join(timeout=0.2)
        reservation_was_waiting = reservation_thread.is_alive()

        release_change.set()
        change_thread.join(timeout=5)
        reservation_thread.join(timeout=5)

        self.assertTrue(reservation_was_waiting, results)
        self.assertCountEqual(results, ["calendar_changed", "reservation_rejected"])
