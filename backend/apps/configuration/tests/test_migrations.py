from datetime import date, time
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
            is_active=False,
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


class ShiftOverlapPreflightMigrationTest(TestCase):
    class _StubQuerySet:
        def __init__(self, rows):
            self._rows = rows

        def values(self, *fields):
            return self._rows

    class _StubManager:
        def __init__(self, rows):
            self._rows = rows

        def filter(self, **kwargs):
            return ShiftOverlapPreflightMigrationTest._StubQuerySet(self._rows)

    class _StubShiftModel:
        def __init__(self, rows):
            self.objects = ShiftOverlapPreflightMigrationTest._StubManager(rows)

    class _StubApps:
        def __init__(self, rows):
            self._model = ShiftOverlapPreflightMigrationTest._StubShiftModel(rows)

        def get_model(self, app_label, model_name):
            return self._model

    def rows(self, **overrides):
        values = {
            "id": 1,
            "name": "Turno",
            "start_time": time(8),
            "end_time": time(12),
            "valid_from": date(2026, 1, 1),
            "valid_until": None,
        }
        values.update(overrides)
        return values

    def migration(self):
        return import_module(
            "apps.configuration.migrations.0008_shift_no_overlap_active"
        )

    def test_preflight_reports_only_overlapping_pairs(self):
        legacy_end = date(2026, 12, 31)
        rows = [
            self.rows(id=1, valid_until=legacy_end),
            self.rows(
                id=2, start_time=time(11), end_time=time(15), valid_until=legacy_end
            ),
            self.rows(
                id=3, start_time=time(13), end_time=time(17), valid_until=legacy_end
            ),
            self.rows(
                id=4, start_time=time(17), end_time=time(21), valid_until=legacy_end
            ),
            self.rows(
                id=5,
                start_time=time(11),
                end_time=time(15),
                valid_from=date(2027, 1, 1),
            ),
        ]

        self.assertEqual(
            self.migration().conflicting_shift_pairs(rows), [(1, 2), (2, 3)]
        )

    def test_preflight_aborts_migration_listing_conflicting_identifiers(self):
        rows = [
            self.rows(id=7),
            self.rows(id=9, start_time=time(11), end_time=time(15)),
        ]
        apps = self._StubApps(rows)

        with self.assertRaises(RuntimeError) as context:
            self.migration().check_conflicting_active_shifts(apps, None)

        message = str(context.exception)
        self.assertIn("#7 e #9", message)
        self.assertIn("shift_no_overlap_active", message)

    def test_preflight_accepts_consistent_shifts(self):
        apps = self._StubApps(
            [
                self.rows(id=1),
                self.rows(id=2, start_time=time(12), end_time=time(17)),
            ]
        )

        self.migration().check_conflicting_active_shifts(apps, None)
