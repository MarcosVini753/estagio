from datetime import time
from importlib import import_module

from django.apps import apps
from django.test import TestCase

from apps.configuration.models import OperatingSchedule, Shift, Weekday


class ShiftSeriesKeyMigrationTest(TestCase):
    def test_groups_legacy_versions_by_name_and_display_order(self):
        first = Shift.objects.create(
            name="1º Turno",
            start_time=time(7, 15),
            end_time=time(13),
            display_order=1,
        )
        second = Shift.objects.create(
            name="1º Turno",
            start_time=time(7, 30),
            end_time=time(13),
            display_order=1,
        )
        other = Shift.objects.create(
            name="2º Turno",
            start_time=time(13),
            end_time=time(17),
            display_order=2,
        )

        migration = import_module("apps.configuration.migrations.0002_shift_series_key")
        migration.populate_series_keys(apps, None)

        first.refresh_from_db()
        second.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(first.series_key, second.series_key)
        self.assertNotEqual(first.series_key, other.series_key)


class RegularOperatingScheduleMigrationTest(TestCase):
    def test_seeds_week_schedule_without_changing_shifts(self):
        shifts_before = list(Shift.objects.values_list("pk", flat=True))
        OperatingSchedule.objects.all().delete()
        migration = import_module(
            "apps.configuration.migrations.0004_seed_regular_operating_schedule"
        )

        migration.seed_regular_schedule(apps, None)

        schedule = OperatingSchedule.objects.get(
            schedule_type=OperatingSchedule.ScheduleType.REGULAR
        )
        self.assertEqual(schedule.days.count(), 7)
        saturday = schedule.days.get(weekday=Weekday.SATURDAY)
        sunday = schedule.days.get(weekday=Weekday.SUNDAY)
        self.assertEqual(saturday.windows.get().closes_at, time(13))
        self.assertFalse(sunday.is_open)
        self.assertFalse(sunday.windows.exists())
        self.assertEqual(
            list(Shift.objects.values_list("pk", flat=True)),
            shifts_before,
        )
