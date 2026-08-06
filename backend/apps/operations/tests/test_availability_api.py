from datetime import datetime, time, timedelta
from unittest.mock import patch

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.computers.models import Computer
from apps.configuration.models import (
    BookingPolicy,
    CalendarException,
    OperatingSchedule,
    Shift,
    Weekday,
)
from apps.configuration.tests.factories import create_operating_schedule
from apps.operations.models import ComputerAllocation, Reservation, UseSession


class AvailabilityAPITest(APITestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.tomorrow = self.today + timedelta(days=1)
        self.computer = Computer.objects.create(code="PC-01")
        Shift.objects.create(
            name="Manhã",
            start_time=time(7, 0),
            end_time=time(10, 0),
            valid_from=self.today - timedelta(days=1),
        )
        OperatingSchedule.objects.all().delete()
        create_operating_schedule(
            valid_from=self.today - timedelta(days=1),
            weekday_windows={
                weekday: [(time(7), time(10))] for weekday in Weekday.values
            },
        )
        BookingPolicy.objects.create(
            slot_duration_minutes=60,
            valid_from=self.today - timedelta(days=1),
            is_active=True,
        )
        self.client.post(
            "/api/v1/demo/select-profile/",
            {
                "profile": "ROOM_USER",
                "user_reference": "aluno-si-001",
                "affiliation_type": "STUDENT",
                "institutional_unit": "Sistemas de Informação",
            },
            format="json",
        )

    def aware(self, target_date, target_time):
        return timezone.make_aware(
            datetime.combine(target_date, target_time),
            timezone.get_current_timezone(),
        )

    def test_slots_show_reservation_and_available_intervals(self):
        Reservation.objects.create(
            user_reference="another-user",
            computer=self.computer,
            starts_at=self.aware(self.tomorrow, time(8, 0)),
            ends_at=self.aware(self.tomorrow, time(9, 0)),
            created_by_profile="ROOM_USER",
        )

        response = self.client.get(
            f"/api/v1/computers/{self.computer.pk}/slots/",
            {"date": self.tomorrow.isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["slots"]), 3)
        self.assertEqual(
            [slot["effective_status"] for slot in response.data["slots"]],
            ["AVAILABLE", "RESERVED", "AVAILABLE"],
        )
        self.assertEqual(
            [slot["selectable"] for slot in response.data["slots"]],
            [True, False, True],
        )

    def test_operational_state_has_precedence_over_reservation(self):
        self.computer.operational_state = Computer.OperationalState.MAINTENANCE
        self.computer.save(update_fields=["operational_state", "updated_at"])
        Reservation.objects.create(
            user_reference="another-user",
            computer=self.computer,
            starts_at=self.aware(self.tomorrow, time(8, 0)),
            ends_at=self.aware(self.tomorrow, time(9, 0)),
            created_by_profile="ROOM_USER",
        )

        response = self.client.get(
            f"/api/v1/computers/{self.computer.pk}/slots/",
            {"date": self.tomorrow.isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            all(
                slot["effective_status"] == "MAINTENANCE"
                for slot in response.data["slots"]
            )
        )

    def test_rejects_date_outside_today_and_tomorrow(self):
        response = self.client.get(
            "/api/v1/computers/availability/",
            {"date": (self.today + timedelta(days=2)).isoformat()},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "DATE_OUTSIDE_ALLOWED_WINDOW")

    def test_active_allocation_is_reported_as_occupied_now(self):
        fixed_now = self.aware(self.today, time(8, 30))
        session = UseSession.objects.create(
            user_reference="another-user",
            started_at=fixed_now - timedelta(minutes=30),
            entry_recorded_by_profile="INTERN",
        )
        ComputerAllocation.objects.create(
            session=session,
            computer=self.computer,
            sequence=1,
            started_at=fixed_now - timedelta(minutes=30),
        )

        with patch(
            "apps.operations.availability.timezone.now",
            return_value=fixed_now,
        ):
            response = self.client.get(
                "/api/v1/computers/availability/",
                {"date": self.today.isoformat()},
            )

        self.assertEqual(response.status_code, 200)
        item = response.data["computers"][0]
        self.assertEqual(item["effective_status_now"], "OCCUPIED")
        self.assertFalse(item["can_start_now"])

    def test_closed_calendar_exception_returns_no_slots(self):
        CalendarException.objects.create(
            date=self.tomorrow,
            exception_type=CalendarException.ExceptionType.CLOSED,
            description="Fechamento de demonstração",
        )

        response = self.client.get(
            f"/api/v1/computers/{self.computer.pk}/slots/",
            {"date": self.tomorrow.isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["slots"], [])

    def test_saturday_stops_at_13_and_returns_room_context(self):
        OperatingSchedule.objects.all().delete()
        create_operating_schedule()
        saturday = datetime(2026, 8, 8, 8, tzinfo=timezone.get_current_timezone())

        with patch(
            "apps.operations.availability.timezone.now",
            return_value=saturday - timedelta(days=1),
        ):
            response = self.client.get(
                f"/api/v1/computers/{self.computer.pk}/slots/",
                {"date": saturday.date().isoformat()},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["room"]["status"], "OPEN")
        self.assertEqual(response.data["room"]["source"], "REGULAR_SCHEDULE")
        self.assertEqual(len(response.data["slots"]), 5)
        self.assertEqual(
            response.data["slots"][-1]["ends_at"],
            self.aware(saturday.date(), time(12, 15)).isoformat(),
        )

    def test_sunday_returns_no_slots_reason_and_cannot_start_now(self):
        OperatingSchedule.objects.all().delete()
        create_operating_schedule()
        sunday_now = datetime(
            2026,
            8,
            9,
            8,
            tzinfo=timezone.get_current_timezone(),
        )

        with patch(
            "apps.operations.availability.timezone.now",
            return_value=sunday_now,
        ):
            response = self.client.get(
                "/api/v1/computers/availability/",
                {"date": sunday_now.date().isoformat()},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["room"]["status"], "CLOSED")
        self.assertIn("domingos", response.data["room"]["reason"])
        self.assertEqual(response.data["computers"][0]["available_slot_count"], 0)
        self.assertFalse(response.data["computers"][0]["can_start_now"])
