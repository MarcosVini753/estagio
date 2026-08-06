from datetime import datetime, time
from importlib import import_module

from django.apps import apps as django_apps
from django.test import TestCase
from django.utils import timezone

from apps.computers.models import Computer
from apps.operations.models import Reservation, UseSession

from .factories import create_reservation, create_use_session

backfill_model_c_deadlines = import_module(
    "apps.operations.migrations.0007_backfill_model_c_deadlines"
).backfill_model_c_deadlines


class ModelCMigrationTest(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.computer = Computer.objects.create(code="PC-01")

    def aware(self, value):
        return timezone.make_aware(
            datetime.combine(self.today, value),
            timezone.get_current_timezone(),
        )

    def test_backfill_derives_deadlines_and_historical_intervals(self):
        reservation = create_reservation(
            user_reference="reserved-user",
            computer=self.computer,
            starts_at=self.aware(time(8)),
            ends_at=self.aware(time(9)),
            check_in_deadline_at=self.aware(time(8, 10)),
            exit_deadline_at=self.aware(time(9, 10)),
            status=Reservation.Status.NO_SHOW,
            no_show_at=None,
            created_by_profile="ROOM_USER",
        )
        reserved_session = create_use_session(
            user_reference="reserved-user",
            reservation=reservation,
            started_at=self.aware(time(8, 3)),
            planned_starts_at=self.aware(time(8, 3)),
            planned_ends_at=self.aware(time(9, 15)),
            exit_deadline_at=self.aware(time(9, 18)),
            ended_at=self.aware(time(8, 45)),
            status=UseSession.Status.FINISHED,
            entry_recorded_by_profile="ROOM_USER",
        )
        historical_session = create_use_session(
            user_reference="historical-user",
            started_at=self.aware(time(10)),
            planned_ends_at=self.aware(time(11)),
            exit_deadline_at=self.aware(time(11, 3)),
            ended_at=self.aware(time(10, 30)),
            status=UseSession.Status.FINISHED,
            entry_recorded_by_profile="ROOM_USER",
        )

        backfill_model_c_deadlines(django_apps, None)

        reservation.refresh_from_db()
        reserved_session.refresh_from_db()
        historical_session.refresh_from_db()
        self.assertEqual(reservation.check_in_deadline_at, self.aware(time(8, 3)))
        self.assertEqual(reservation.exit_deadline_at, self.aware(time(9, 3)))
        self.assertEqual(reservation.no_show_at, self.aware(time(8, 3)))
        self.assertEqual(reserved_session.planned_starts_at, reservation.starts_at)
        self.assertEqual(reserved_session.planned_ends_at, reservation.ends_at)
        self.assertEqual(
            reserved_session.exit_deadline_at, reservation.exit_deadline_at
        )
        self.assertEqual(historical_session.planned_starts_at, self.aware(time(10)))
        self.assertEqual(historical_session.planned_ends_at, self.aware(time(10, 30)))
        self.assertEqual(historical_session.exit_deadline_at, self.aware(time(10, 33)))

    def test_backfill_requires_all_legacy_sessions_to_be_finished(self):
        create_use_session(
            user_reference="active-user",
            started_at=self.aware(time(8)),
            entry_recorded_by_profile="ROOM_USER",
        )

        with self.assertRaisesMessage(
            RuntimeError,
            "Finalize as sessões legadas ativas antes de aplicar o Modelo C.",
        ):
            backfill_model_c_deadlines(django_apps, None)
