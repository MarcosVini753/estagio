from datetime import time
from threading import Barrier, Thread

from django.db import close_old_connections, connections
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.configuration.models import Shift
from apps.configuration.services import create_shift


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
