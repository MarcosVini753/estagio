from datetime import datetime, time, timedelta

from django.test import SimpleTestCase
from django.utils import timezone

from apps.configuration.calendar import OperatingDayResult, OperatingWindowResult
from apps.operations.slotting import (
    calculate_interval,
    immediate_planned_end_options,
    validate_immediate_planned_end,
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

    def test_immediate_end_options_start_at_the_next_fixed_grid_mark(self):
        options, limited_by = immediate_planned_end_options(
            starts_at=self.starts_at + timedelta(minutes=6),
            operating_day=self.operating_day,
            limits=[
                (self.starts_at + timedelta(minutes=51), "NEXT_RESERVATION"),
            ],
        )

        self.assertEqual(
            options,
            [
                self.starts_at + timedelta(minutes=15),
                self.starts_at + timedelta(minutes=30),
                self.starts_at + timedelta(minutes=45),
            ],
        )
        self.assertEqual(limited_by, "NEXT_RESERVATION")

    def test_immediate_end_may_match_the_next_reservation_start(self):
        options, limited_by = immediate_planned_end_options(
            starts_at=self.starts_at + timedelta(minutes=6),
            operating_day=self.operating_day,
            limits=[
                (self.starts_at + timedelta(minutes=30), "USER_RESERVATION"),
            ],
        )

        self.assertEqual(
            options,
            [
                self.starts_at + timedelta(minutes=15),
                self.starts_at + timedelta(minutes=30),
            ],
        )
        self.assertEqual(limited_by, "USER_RESERVATION")

    def test_immediate_end_requires_a_grid_mark_after_actual_start(self):
        start = self.starts_at + timedelta(minutes=6)
        validate_immediate_planned_end(
            starts_at=start,
            planned_ends_at=self.starts_at + timedelta(minutes=15),
            operating_day=self.operating_day,
        )

        with self.assertRaises(ValueError):
            validate_immediate_planned_end(
                starts_at=start,
                planned_ends_at=self.starts_at + timedelta(minutes=14),
                operating_day=self.operating_day,
            )

    def test_immediate_end_must_stay_in_the_same_window_of_a_split_day(self):
        split_day = OperatingDayResult(
            date=self.starts_at.date(),
            status="OPEN",
            source="REGULAR_SCHEDULE",
            reason="",
            windows=(
                OperatingWindowResult(time(7, 15), time(9)),
                OperatingWindowResult(time(10), time(12)),
            ),
        )

        options, _ = immediate_planned_end_options(
            starts_at=self.starts_at + timedelta(minutes=51),
            operating_day=split_day,
        )

        self.assertEqual(options, [self.starts_at + timedelta(hours=1)])
        with self.assertRaises(ValueError):
            validate_immediate_planned_end(
                starts_at=self.starts_at + timedelta(minutes=51),
                planned_ends_at=self.starts_at + timedelta(hours=2),
                operating_day=split_day,
            )
