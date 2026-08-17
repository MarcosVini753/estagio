from datetime import datetime, time, timedelta
from importlib import import_module

from django.apps import apps as django_apps
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from apps.computers.models import Computer
from apps.operations.models import UseSession

from .factories import create_use_session

backfill_model_c_deadlines = import_module(
    "apps.operations.migrations.0007_backfill_model_c_deadlines"
).backfill_model_c_deadlines
validate_operation_state_metadata = import_module(
    "apps.operations.migrations.0011_enforce_operation_state_metadata"
).validate_operation_state_metadata


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

        historical_session.refresh_from_db()
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

    def test_backfill_normalizes_zero_duration_legacy_session(self):
        instant = self.aware(time(10))
        session = create_use_session(
            user_reference="zero-duration-user",
            started_at=instant,
            planned_ends_at=instant + timedelta(minutes=15),
            exit_deadline_at=instant + timedelta(minutes=18),
            ended_at=instant,
            status=UseSession.Status.FINISHED,
            entry_recorded_by_profile="ROOM_USER",
        )

        backfill_model_c_deadlines(django_apps, None)

        session.refresh_from_db()
        self.assertEqual(session.planned_starts_at, instant)
        self.assertEqual(session.planned_ends_at, instant + timedelta.resolution)
        self.assertEqual(session.exit_deadline_at, instant + timedelta(minutes=3))


class OperationStatePreflightMigrationTest(TransactionTestCase):
    migrate_from = ("operations", "0010_allow_early_reservation_check_in")

    def test_preflight_reports_model_and_inconsistent_ids(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        session_model = old_apps.get_model("operations", "UseSession")
        instant = timezone.now()
        session = session_model.objects.create(
            user_reference="legacy-inconsistent",
            started_at=instant,
            planned_starts_at=instant,
            planned_ends_at=instant + timedelta(minutes=15),
            exit_deadline_at=instant + timedelta(minutes=18),
            ended_at=None,
            status="FINISHED",
            entry_recorded_by_profile="ROOM_USER",
            exit_recorded_by_profile="",
        )

        with self.assertRaisesMessage(
            RuntimeError,
            f"UseSession: IDs [{session.pk}]",
        ):
            validate_operation_state_metadata(old_apps, None)

        session.delete()
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
