from datetime import date, datetime, time

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.configuration.models import (
    CalendarException,
    OperatingSchedule,
    OperatingScheduleDay,
    OperatingWindow,
    RoomNotice,
    Shift,
    Weekday,
)


class ConfigurationModelTest(TestCase):
    def test_shift_rejects_invalid_period_on_full_clean(self):
        shift = Shift(name="Inválido", start_time=time(13, 0), end_time=time(12, 0))

        with self.assertRaises(ValidationError):
            shift.full_clean()

    def test_special_hours_requires_open_and_close(self):
        exception = CalendarException(
            date="2026-07-14",
            exception_type=CalendarException.ExceptionType.SPECIAL_HOURS,
        )

        with self.assertRaises(ValidationError):
            exception.full_clean()

    def test_temporary_schedule_requires_end_and_valid_period(self):
        missing_end = OperatingSchedule(
            name="Recesso",
            schedule_type=OperatingSchedule.ScheduleType.TEMPORARY,
            valid_from=date(2026, 12, 1),
            created_by_profile="LIBRARY_SUPERVISOR",
        )
        invalid_period = OperatingSchedule(
            name="Recesso",
            schedule_type=OperatingSchedule.ScheduleType.TEMPORARY,
            valid_from=date(2026, 12, 10),
            valid_until=date(2026, 12, 1),
            created_by_profile="LIBRARY_SUPERVISOR",
        )

        with self.assertRaises(ValidationError):
            missing_end.full_clean()
        with self.assertRaises(ValidationError):
            invalid_period.full_clean()

    def test_closed_day_rejects_window_and_windows_do_not_overlap(self):
        schedule = OperatingSchedule.objects.create(
            name="Recesso",
            schedule_type=OperatingSchedule.ScheduleType.TEMPORARY,
            valid_from=date(2026, 12, 1),
            valid_until=date(2026, 12, 31),
            created_by_profile="LIBRARY_SUPERVISOR",
        )
        closed_day = OperatingScheduleDay.objects.create(
            schedule=schedule,
            weekday=Weekday.SUNDAY,
            is_open=False,
        )
        invalid_window = OperatingWindow(
            schedule_day=closed_day,
            opens_at=time(8),
            closes_at=time(12),
        )
        open_day = OperatingScheduleDay.objects.create(
            schedule=schedule,
            weekday=Weekday.MONDAY,
            is_open=True,
        )
        OperatingWindow.objects.create(
            schedule_day=open_day,
            opens_at=time(8),
            closes_at=time(12),
        )
        overlapping_window = OperatingWindow(
            schedule_day=open_day,
            opens_at=time(11),
            closes_at=time(13),
        )

        with self.assertRaises(ValidationError):
            invalid_window.full_clean()
        with self.assertRaises(ValidationError):
            overlapping_window.full_clean()

    def test_room_notice_rejects_invalid_period_and_blank_message(self):
        notice = RoomNotice(
            notice_type=RoomNotice.NoticeType.CLOSURE,
            title="Fechamento",
            message=" ",
            effective_from=date(2026, 8, 10),
            effective_until=date(2026, 8, 9),
            visible_from=datetime(2026, 8, 5, 12),
            created_by_profile="LIBRARY_SUPERVISOR",
        )

        with self.assertRaises(ValidationError):
            notice.full_clean()

    def test_active_schedules_of_same_type_cannot_overlap(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                OperatingSchedule.objects.create(
                    name="Outro horário regular",
                    schedule_type=OperatingSchedule.ScheduleType.REGULAR,
                    valid_from=date(2026, 1, 1),
                    created_by_profile="LIBRARY_SUPERVISOR",
                )
