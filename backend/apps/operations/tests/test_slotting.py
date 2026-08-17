from datetime import datetime, time, timedelta

from django.test import SimpleTestCase
from django.utils import timezone

from apps.configuration.calendar import OperatingDayResult, OperatingWindowResult
from apps.operations.slotting import (
    calculate_interval,
    calculate_max_immediate_slot_count,
    validate_interval_inside_operating_window,
    validate_reservation_slot_start,
)


class SlottingTest(SimpleTestCase):
    def setUp(self):
        self.starts_at = timezone.make_aware(
            datetime(2026, 8, 7, 8),
            timezone.get_current_timezone(),
        )
        self.operating_day = OperatingDayResult(
            date=self.starts_at.date(),
            status="OPEN",
            source="REGULAR_SCHEDULE",
            reason="",
            windows=(OperatingWindowResult(time(7, 15), time(10)),),
        )

    def test_four_slots_generate_sixty_minute_interval(self):
        ends_at = calculate_interval(self.starts_at, 4)

        self.assertEqual(ends_at, self.starts_at + timedelta(minutes=60))

    def test_slot_count_must_be_positive_integer(self):
        for slot_count in (0, -1, True, 1.5):
            with self.subTest(slot_count=slot_count), self.assertRaises(ValueError):
                calculate_interval(self.starts_at, slot_count)

        with self.assertRaises(ValueError):
            calculate_interval(self.starts_at, 10**100)

    def test_reservation_start_must_align_to_fifteen_minute_grid(self):
        validate_reservation_slot_start(self.starts_at, self.operating_day)

        with self.assertRaises(ValueError):
            validate_reservation_slot_start(
                self.starts_at + timedelta(minutes=1),
                self.operating_day,
            )

    def test_interval_must_fit_inside_one_operating_window(self):
        validate_interval_inside_operating_window(
            self.starts_at,
            self.starts_at + timedelta(hours=2),
            self.operating_day,
        )

        with self.assertRaises(ValueError):
            validate_interval_inside_operating_window(
                self.starts_at,
                self.starts_at + timedelta(hours=3),
                self.operating_day,
            )

    def test_maximum_immediate_slots_stop_before_earliest_limit(self):
        slot_count, planned_end, limited_by = calculate_max_immediate_slot_count(
            starts_at=self.starts_at + timedelta(minutes=6),
            operating_day=self.operating_day,
            limits=[
                (self.starts_at + timedelta(minutes=51), "NEXT_RESERVATION"),
            ],
        )

        self.assertEqual(slot_count, 3)
        self.assertEqual(planned_end, self.starts_at + timedelta(minutes=51))
        self.assertEqual(limited_by, "NEXT_RESERVATION")

    def test_maximum_immediate_slots_report_zero_when_limit_is_too_close(self):
        slot_count, planned_end, limited_by = calculate_max_immediate_slot_count(
            starts_at=self.starts_at,
            operating_day=self.operating_day,
            limits=[
                (self.starts_at + timedelta(minutes=10), "USER_RESERVATION"),
            ],
        )

        self.assertEqual(slot_count, 0)
        self.assertIsNone(planned_end)
        self.assertEqual(limited_by, "USER_RESERVATION")
