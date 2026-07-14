from datetime import time

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.configuration.models import CalendarException, Shift


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
