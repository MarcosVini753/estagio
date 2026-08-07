from datetime import date, datetime, time, timedelta

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class DomainNormalizationMigrationTest(TransactionTestCase):
    migrate_from = [
        ("configuration", "0006_remove_configurable_slot_and_tolerance"),
        ("operations", "0008_enforce_model_c_constraints"),
    ]
    migrate_to = [
        (
            "configuration",
            "0007_remove_bookingpolicy_one_active_booking_policy_and_more",
        ),
        ("operations", "0009_remove_reservation_invalidated_at_and_more"),
    ]

    def setUp(self):
        super().setUp()
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_from)
        old_apps = self.executor.loader.project_state(self.migrate_from).apps
        Computer = old_apps.get_model("computers", "Computer")
        BookingPolicy = old_apps.get_model("configuration", "BookingPolicy")
        CalendarException = old_apps.get_model("configuration", "CalendarException")
        Reservation = old_apps.get_model("operations", "Reservation")

        computer = Computer.objects.create(code="PC-MIGRATION")
        self.old_policy = BookingPolicy.objects.create(
            valid_from=date(2025, 1, 1),
            is_active=False,
        )
        self.current_policy = BookingPolicy.objects.create(
            valid_from=date(2026, 1, 1),
            is_active=True,
        )
        CalendarException.objects.create(
            date=date(2026, 10, 28),
            exception_type="OPTIONAL_HOLIDAY",
            description="Ponto facultativo.",
        )
        zone = timezone.get_current_timezone()
        starts_at = timezone.make_aware(
            datetime.combine(date(2026, 2, 1), time(8)), zone
        )
        ends_at = starts_at + timedelta(hours=1)
        deadline = starts_at + timedelta(minutes=3)
        self.no_show = Reservation.objects.create(
            user_reference="no-show",
            computer=computer,
            starts_at=starts_at,
            ends_at=ends_at,
            check_in_deadline_at=deadline,
            exit_deadline_at=ends_at + timedelta(minutes=3),
            no_show_at=deadline + timedelta(minutes=1),
            status="NO_SHOW",
            created_by_profile="INTERN",
        )
        self.invalidated = Reservation.objects.create(
            user_reference="invalidated",
            computer=computer,
            starts_at=starts_at + timedelta(hours=2),
            ends_at=ends_at + timedelta(hours=2),
            check_in_deadline_at=deadline + timedelta(hours=2),
            exit_deadline_at=ends_at + timedelta(hours=2, minutes=3),
            status="INVALIDATED",
            created_by_profile="ROOM_USER",
            invalidated_at=deadline,
            invalidated_by_profile="INTERN",
            invalidation_reason="Fechamento excepcional.",
        )

        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_to)
        self.apps = self.executor.loader.project_state(self.migrate_to).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_preserves_policy_and_reservation_history(self):
        BookingPolicy = self.apps.get_model("configuration", "BookingPolicy")
        CalendarException = self.apps.get_model("configuration", "CalendarException")
        Reservation = self.apps.get_model("operations", "Reservation")

        old_policy = BookingPolicy.objects.get(pk=self.old_policy.pk)
        current_policy = BookingPolicy.objects.get(pk=self.current_policy.pk)
        no_show = Reservation.objects.get(pk=self.no_show.pk)
        invalidated = Reservation.objects.get(pk=self.invalidated.pk)

        self.assertEqual(old_policy.valid_until, date(2025, 12, 31))
        self.assertIsNone(current_policy.valid_until)
        self.assertEqual(
            CalendarException.objects.get(date=date(2026, 10, 28)).exception_type,
            "CLOSED",
        )
        self.assertEqual(no_show.status, "CANCELLED")
        self.assertEqual(no_show.cancelled_by_profile, "SYSTEM_ADMIN")
        self.assertEqual(no_show.cancellation_reason, "Prazo de check-in expirado.")
        self.assertEqual(no_show.booking_policy_id, current_policy.pk)
        self.assertEqual(no_show.created_by_profile, "ROOM_MONITOR")
        self.assertEqual(invalidated.status, "CANCELLED")
        self.assertEqual(invalidated.cancelled_by_profile, "ROOM_MONITOR")
        self.assertEqual(
            invalidated.cancellation_reason,
            "Fechamento excepcional.",
        )
