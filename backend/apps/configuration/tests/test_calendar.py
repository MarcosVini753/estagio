from datetime import date, time

from django.test import TestCase

from apps.configuration.calendar import resolve_operating_day
from apps.configuration.models import CalendarException, OperatingSchedule
from apps.core.api.errors import OperatingScheduleRequired

from .factories import create_operating_schedule


class OperatingCalendarResolverTest(TestCase):
    def setUp(self):
        OperatingSchedule.objects.all().delete()

    def test_regular_schedule_closes_saturday_at_13_and_sunday(self):
        create_operating_schedule()

        saturday = resolve_operating_day(date(2026, 8, 8))
        sunday = resolve_operating_day(date(2026, 8, 9))

        self.assertEqual(saturday.status, "OPEN")
        self.assertEqual(
            [(window.opens_at, window.closes_at) for window in saturday.windows],
            [(time(7, 15), time(13))],
        )
        self.assertEqual(sunday.status, "CLOSED")
        self.assertEqual(sunday.source, "REGULAR_SCHEDULE")
        self.assertEqual(sunday.windows, ())

    def test_missing_regular_schedule_is_configuration_error(self):
        with self.assertRaises(OperatingScheduleRequired):
            resolve_operating_day(date(2026, 8, 10))

    def test_exception_precedes_temporary_and_regular_schedules(self):
        create_operating_schedule()
        create_operating_schedule(
            schedule_type=OperatingSchedule.ScheduleType.TEMPORARY,
            valid_from=date(2026, 8, 3),
            valid_until=date(2026, 8, 14),
            weekday_windows={weekday: [(time(8), time(13))] for weekday in range(5)},
        )
        CalendarException.objects.create(
            date=date(2026, 8, 10),
            exception_type=CalendarException.ExceptionType.CLOSED,
            description="Manutenção elétrica.",
        )

        result = resolve_operating_day(date(2026, 8, 10))

        self.assertEqual(result.status, "CLOSED")
        self.assertEqual(result.source, "CALENDAR_EXCEPTION")
        self.assertEqual(result.reason, "Manutenção elétrica.")

    def test_regular_schedule_returns_after_temporary_period(self):
        create_operating_schedule()
        create_operating_schedule(
            schedule_type=OperatingSchedule.ScheduleType.TEMPORARY,
            valid_from=date(2026, 8, 3),
            valid_until=date(2026, 8, 14),
            weekday_windows={weekday: [(time(8), time(13))] for weekday in range(5)},
        )

        during = resolve_operating_day(date(2026, 8, 10))
        after = resolve_operating_day(date(2026, 8, 17))

        self.assertEqual(during.source, "TEMPORARY_SCHEDULE")
        self.assertEqual(during.windows[0].opens_at, time(8))
        self.assertEqual(after.source, "REGULAR_SCHEDULE")
        self.assertEqual(after.windows[0].opens_at, time(7, 15))
