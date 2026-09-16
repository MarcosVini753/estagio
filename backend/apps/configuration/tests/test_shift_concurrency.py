from datetime import datetime, time, timedelta
from threading import Barrier, Event, Thread
from unittest.mock import patch

from django.db import close_old_connections, connections
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.computers.models import Computer
from apps.configuration.models import BookingPolicy, OperatingSchedule, Shift, Weekday
from apps.configuration.services import create_shift, update_shift
from apps.configuration.services import shifts as shift_services
from apps.configuration.tests.factories import create_operating_schedule
from apps.operations.models import UseSession
from apps.operations.services import start_usage_session
from apps.operations.services import usage_sessions


class ShiftWriteConcurrencyTest(TransactionTestCase):
    def setUp(self):
        self.today = timezone.localdate()

    def shift_values(self, name):
        return {
            "name": name,
            "start_time": time(8, 0),
            "end_time": time(12, 0),
            "display_order": 1,
            "valid_from": self.today,
            "valid_until": None,
            "is_active": True,
        }

    def run_simultaneously(self, targets):
        barrier = Barrier(len(targets))
        results = []

        def runner(target):
            close_old_connections()
            try:
                barrier.wait()
                target()
                results.append("created")
            except ValidationError:
                results.append("rejected")
            finally:
                connections.close_all()

        threads = [Thread(target=runner, args=(target,)) for target in targets]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        return results

    def test_simultaneous_overlapping_creations_keep_only_one_shift(self):
        results = self.run_simultaneously(
            [
                lambda: create_shift(
                    values=self.shift_values("Turno A"),
                    actor_profile="LIBRARY_SUPERVISOR",
                ),
                lambda: create_shift(
                    values=self.shift_values("Turno B"),
                    actor_profile="LIBRARY_SUPERVISOR",
                ),
            ]
        )

        self.assertCountEqual(results, ["created", "rejected"])
        self.assertEqual(Shift.objects.filter(is_active=True).count(), 1)

    def test_entry_waits_for_shift_update_before_classifying_session(self):
        shift = Shift.objects.create(
            name="Turno inicial",
            start_time=time(7, 15),
            end_time=time(12),
            valid_from=self.today - timedelta(days=1),
        )
        computer = Computer.objects.create(code="PC-01")
        BookingPolicy.objects.create(valid_from=self.today - timedelta(days=1))
        OperatingSchedule.objects.all().delete()
        create_operating_schedule(
            valid_from=self.today - timedelta(days=1),
            weekday_windows={
                weekday: [(time(7), time(22))] for weekday in Weekday.values
            },
        )
        current = timezone.make_aware(
            datetime.combine(self.today, time(8)),
            timezone.get_current_timezone(),
        )
        update_holds_lock = Event()
        release_update = Event()
        entry_requested_lock = Event()
        errors = []
        original_validate = shift_services._validated_values
        original_entry_lock = usage_sessions.lock_shift_configuration

        def pause_update_validation(*args, **kwargs):
            update_holds_lock.set()
            release_update.wait(timeout=5)
            return original_validate(*args, **kwargs)

        def observe_entry_lock():
            entry_requested_lock.set()
            return original_entry_lock()

        def run_update():
            close_old_connections()
            try:
                update_shift(
                    shift_id=shift.pk,
                    values={"start_time": time(9)},
                    actor_profile="LIBRARY_SUPERVISOR",
                )
            except Exception as error:  # pragma: no cover - asserted below
                errors.append(error)
            finally:
                connections.close_all()

        def run_entry():
            close_old_connections()
            try:
                start_usage_session(
                    computer_id=computer.pk,
                    planned_ends_at=current + timedelta(minutes=30),
                    actor_profile="ROOM_USER",
                    actor_reference="aluno-concorrente",
                    affiliation_type="STUDENT",
                    institutional_unit="Sistemas de Informação",
                    now=current,
                )
            except Exception as error:  # pragma: no cover - asserted below
                errors.append(error)
            finally:
                connections.close_all()

        with (
            patch.object(
                shift_services,
                "_validated_values",
                side_effect=pause_update_validation,
            ),
            patch.object(
                usage_sessions,
                "lock_shift_configuration",
                side_effect=observe_entry_lock,
            ),
        ):
            update_thread = Thread(target=run_update)
            update_thread.start()
            self.assertTrue(update_holds_lock.wait(timeout=5))

            entry_thread = Thread(target=run_entry)
            entry_thread.start()
            self.assertTrue(entry_requested_lock.wait(timeout=5))
            self.assertFalse(UseSession.objects.exists())

            release_update.set()
            update_thread.join(timeout=10)
            entry_thread.join(timeout=10)

        self.assertFalse(update_thread.is_alive())
        self.assertFalse(entry_thread.is_alive())
        self.assertEqual(errors, [])
        self.assertIsNone(UseSession.objects.get().start_shift)
