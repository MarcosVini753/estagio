from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.computers.models import Computer, ComputerOperationalStateChange
from apps.configuration.models import (
    BookingPolicy,
    CalendarException,
    OperatingSchedule,
    Shift,
)
from apps.core.enums import AffiliationType
from apps.occurrences.models import Occurrence
from apps.operations.models import ComputerAllocation, Reservation, UseSession
from apps.operations.tests.factories import create_use_session


class SeedReportDemoDataTest(TestCase):
    def run_seed(self, *, days=10, seed=12345, reset=False):
        output = StringIO()
        call_command(
            "seed_report_demo_data",
            days=days,
            seed=seed,
            reset=reset,
            stdout=output,
        )
        return output.getvalue()

    def counts(self):
        return {
            "computers": Computer.objects.count(),
            "shifts": Shift.objects.count(),
            "sessions": UseSession.objects.count(),
            "allocations": ComputerAllocation.objects.count(),
            "reservations": Reservation.objects.count(),
            "occurrences": Occurrence.objects.count(),
            "calendar": CalendarException.objects.count(),
            "operating_schedules": OperatingSchedule.objects.count(),
            "state_changes": ComputerOperationalStateChange.objects.count(),
        }

    def test_generates_operational_history_for_report_indicators(self):
        output = self.run_seed(days=10, seed=12345)

        self.assertEqual(Computer.objects.count(), 8)
        self.assertEqual(Shift.objects.count(), 3)
        self.assertGreater(UseSession.objects.count(), 0)
        self.assertLess(UseSession.objects.count(), 27)
        self.assertEqual(
            OperatingSchedule.objects.filter(
                schedule_type=OperatingSchedule.ScheduleType.REGULAR,
                is_active=True,
            ).count(),
            1,
        )
        self.assertGreater(
            ComputerAllocation.objects.count(), UseSession.objects.count()
        )
        self.assertEqual(
            set(UseSession.objects.values_list("affiliation_type", flat=True)),
            {
                AffiliationType.STUDENT,
                AffiliationType.PROFESSOR,
                AffiliationType.TECHNICAL_STAFF,
            },
        )
        self.assertEqual(
            set(Reservation.objects.values_list("status", flat=True)),
            set(Reservation.Status.values),
        )
        self.assertEqual(
            set(Occurrence.objects.values_list("status", flat=True)),
            {Occurrence.Status.OPEN, Occurrence.Status.RESOLVED},
        )
        self.assertEqual(
            set(CalendarException.objects.values_list("exception_type", flat=True)),
            {
                CalendarException.ExceptionType.CLOSED,
                CalendarException.ExceptionType.SPECIAL_HOURS,
            },
        )
        self.assertEqual(ComputerOperationalStateChange.objects.count(), 2)
        self.assertIn("10 dias, semente 12345", output)

    def test_second_execution_does_not_duplicate_data(self):
        self.run_seed(days=10, seed=12345)
        first_counts = self.counts()

        self.run_seed(days=10, seed=12345)

        self.assertEqual(self.counts(), first_counts)

    def test_reset_preserves_manual_data_and_canonical_computer_values(self):
        manual_computer = Computer.objects.create(
            code="PC-01",
            description="Descrição manual",
        )
        external_computer = Computer.objects.create(code="MANUAL-01")
        manual_session = create_use_session(
            user_reference="manual-user",
            status=UseSession.Status.FINISHED,
            ended_at="2026-01-01T09:00:00-05:00",
            started_at="2026-01-01T08:00:00-05:00",
            entry_recorded_by_profile="ROOM_USER",
        )
        ComputerAllocation.objects.create(
            session=manual_session,
            computer=external_computer,
            sequence=1,
            started_at="2026-01-01T08:00:00-05:00",
            ended_at="2026-01-01T09:00:00-05:00",
        )
        self.run_seed(days=10, seed=12345)

        self.run_seed(days=10, seed=12345, reset=True)

        manual_computer.refresh_from_db()
        self.assertEqual(manual_computer.description, "Descrição manual")
        self.assertTrue(Computer.objects.filter(code="MANUAL-01").exists())
        self.assertTrue(
            UseSession.objects.filter(user_reference="manual-user").exists()
        )

    def test_same_seed_recreates_the_same_timeline(self):
        self.run_seed(days=10, seed=77, reset=True)
        first_timeline = list(
            UseSession.objects.filter(user_reference__startswith="demo-report-")
            .order_by("started_at", "user_reference")
            .values_list(
                "user_reference",
                "started_at",
                "ended_at",
                "affiliation_type",
                "institutional_unit",
            )
        )

        self.run_seed(days=10, seed=77, reset=True)
        second_timeline = list(
            UseSession.objects.filter(user_reference__startswith="demo-report-")
            .order_by("started_at", "user_reference")
            .values_list(
                "user_reference",
                "started_at",
                "ended_at",
                "affiliation_type",
                "institutional_unit",
            )
        )

        self.assertEqual(second_timeline, first_timeline)

    def test_requires_at_least_three_days(self):
        with self.assertRaises(CommandError):
            self.run_seed(days=2)

    def test_seed_extends_booking_policy_to_cover_historical_range(self):
        from datetime import timedelta

        from django.utils import timezone

        earliest = timezone.localdate() - timedelta(days=10)
        BookingPolicy.objects.create(valid_from=timezone.localdate())

        self.run_seed(days=10, seed=12345)

        policy = BookingPolicy.objects.order_by("valid_from").first()
        self.assertIsNotNone(policy)
        self.assertLessEqual(policy.valid_from, earliest)
        self.assertTrue(Reservation.objects.filter(booking_policy=policy).exists())
