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
from apps.operations.models import ComputerAllocation

from .factories import create_reservation, create_use_session


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
            valid_from=self.today - timedelta(days=1),
        )
        self.client.post(
            "/api/demo/select-profile/",
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
        create_reservation(
            user_reference="another-user",
            computer=self.computer,
            starts_at=self.aware(self.tomorrow, time(8, 0)),
            ends_at=self.aware(self.tomorrow, time(9, 0)),
            created_by_profile="ROOM_USER",
        )

        response = self.client.get(
            f"/api/computers/{self.computer.pk}/slots/",
            {"date": self.tomorrow.isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["immediate_usage"]["planned_end_options"],
            [],
        )
        self.assertEqual(len(response.data["slots"]), 12)
        self.assertEqual(
            [slot["effective_status"] for slot in response.data["slots"]],
            ["AVAILABLE"] * 4 + ["RESERVED"] * 4 + ["AVAILABLE"] * 4,
        )
        self.assertEqual(
            [slot["selectable"] for slot in response.data["slots"]],
            [True] * 4 + [False] * 4 + [True] * 4,
        )

    def test_operational_state_has_precedence_over_reservation(self):
        self.computer.operational_state = Computer.OperationalState.MAINTENANCE
        self.computer.save(update_fields=["operational_state", "updated_at"])
        create_reservation(
            user_reference="another-user",
            computer=self.computer,
            starts_at=self.aware(self.tomorrow, time(8, 0)),
            ends_at=self.aware(self.tomorrow, time(9, 0)),
            created_by_profile="ROOM_USER",
        )

        response = self.client.get(
            f"/api/computers/{self.computer.pk}/slots/",
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
            "/api/computers/availability/",
            {"date": (self.today + timedelta(days=2)).isoformat()},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "DATE_OUTSIDE_ALLOWED_WINDOW")

    def test_active_allocation_is_reported_as_occupied_now(self):
        fixed_now = self.aware(self.today, time(8, 30))
        session = create_use_session(
            user_reference="another-user",
            started_at=fixed_now - timedelta(minutes=30),
            planned_ends_at=fixed_now + timedelta(minutes=30),
            exit_deadline_at=fixed_now + timedelta(minutes=33),
            entry_recorded_by_profile="ROOM_MONITOR",
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
                "/api/computers/availability/",
                {"date": self.today.isoformat()},
            )

        self.assertEqual(response.status_code, 200)
        item = response.data["computers"][0]
        self.assertEqual(item["effective_status_now"], "OCCUPIED")
        self.assertFalse(item["can_start_now"])

    def test_active_allocation_uses_planned_end_for_future_slots(self):
        fixed_now = self.aware(self.today, time(8, 5))
        session = create_use_session(
            user_reference="another-user",
            started_at=self.aware(self.today, time(8)),
            planned_ends_at=self.aware(self.today, time(8, 30)),
            exit_deadline_at=self.aware(self.today, time(8, 33)),
            entry_recorded_by_profile="ROOM_MONITOR",
        )
        ComputerAllocation.objects.create(
            session=session,
            computer=self.computer,
            sequence=1,
            started_at=self.aware(self.today, time(8)),
        )

        with patch(
            "apps.operations.availability.timezone.now",
            return_value=fixed_now,
        ):
            response = self.client.get(
                f"/api/computers/{self.computer.pk}/slots/",
                {"date": self.today.isoformat()},
            )

        slot_after_planned_end = next(
            slot
            for slot in response.data["slots"]
            if slot["starts_at"] == self.aware(self.today, time(8, 30)).isoformat()
        )
        self.assertEqual(slot_after_planned_end["effective_status"], "AVAILABLE")
        self.assertTrue(slot_after_planned_end["selectable"])

    def test_immediate_usage_reports_limit_from_next_reservation(self):
        fixed_now = self.aware(self.today, time(8, 21))
        create_reservation(
            user_reference="another-user",
            computer=self.computer,
            starts_at=self.aware(self.today, time(9)),
            ends_at=self.aware(self.today, time(10)),
            created_by_profile="ROOM_USER",
        )

        with patch(
            "apps.operations.availability.timezone.now",
            return_value=fixed_now,
        ):
            response = self.client.get(
                "/api/computers/availability/",
                {"date": self.today.isoformat()},
            )

        immediate = response.data["computers"][0]["immediate_usage"]
        self.assertTrue(immediate["can_start_now"])
        self.assertNotIn("max_slot_count", immediate)
        self.assertNotIn("planned_end_options", immediate)
        self.assertEqual(
            immediate["max_planned_ends_at"],
            self.aware(self.today, time(9)).isoformat(),
        )
        self.assertEqual(immediate["limited_by"], "NEXT_RESERVATION")

    def test_immediate_usage_reports_room_closing_limit(self):
        fixed_now = self.aware(self.today, time(9, 21))

        with patch(
            "apps.operations.availability.timezone.now",
            return_value=fixed_now,
        ):
            response = self.client.get(
                "/api/computers/availability/",
                {"date": self.today.isoformat()},
            )

        immediate = response.data["computers"][0]["immediate_usage"]
        self.assertEqual(
            immediate["max_planned_ends_at"],
            self.aware(self.today, time(10)).isoformat(),
        )
        self.assertEqual(immediate["limited_by"], "ROOM_CLOSING")

    def test_computer_detail_returns_server_calculated_planned_end_options(self):
        fixed_now = self.aware(self.today, time(8, 21))
        create_reservation(
            user_reference="another-user",
            computer=self.computer,
            starts_at=self.aware(self.today, time(9)),
            ends_at=self.aware(self.today, time(10)),
            created_by_profile="ROOM_USER",
        )

        with patch(
            "apps.operations.availability.timezone.now",
            return_value=fixed_now,
        ):
            response = self.client.get(
                f"/api/computers/{self.computer.pk}/slots/",
                {"date": self.today.isoformat()},
            )

        immediate = response.data["immediate_usage"]
        self.assertEqual(
            immediate["planned_end_options"],
            [
                self.aware(self.today, time(8, 30)).isoformat(),
                self.aware(self.today, time(8, 45)).isoformat(),
                self.aware(self.today, time(9)).isoformat(),
            ],
        )

    def test_immediate_usage_reports_unavailable_computer(self):
        self.computer.operational_state = Computer.OperationalState.INACTIVE
        self.computer.save(update_fields=["operational_state", "updated_at"])
        fixed_now = self.aware(self.today, time(8))

        with patch(
            "apps.operations.availability.timezone.now",
            return_value=fixed_now,
        ):
            response = self.client.get(
                "/api/computers/availability/",
                {"date": self.today.isoformat()},
            )

        immediate = response.data["computers"][0]["immediate_usage"]
        self.assertFalse(immediate["can_start_now"])
        self.assertIsNone(immediate["max_planned_ends_at"])
        self.assertEqual(immediate["limited_by"], "COMPUTER_UNAVAILABLE")

    def test_effective_status_now_does_not_anticipate_upcoming_reservation(self):
        fixed_now = self.aware(self.today, time(8, 21))
        create_reservation(
            user_reference="another-user",
            computer=self.computer,
            starts_at=self.aware(self.today, time(8, 21, 30)),
            ends_at=self.aware(self.today, time(8, 36, 30)),
            created_by_profile="ROOM_USER",
        )

        with patch(
            "apps.operations.availability.timezone.now",
            return_value=fixed_now,
        ):
            response = self.client.get(
                "/api/computers/availability/",
                {"date": self.today.isoformat()},
            )

        item = response.data["computers"][0]
        self.assertEqual(item["effective_status_now"], "AVAILABLE")
        self.assertFalse(item["immediate_usage"]["can_start_now"])
        self.assertEqual(item["immediate_usage"]["limited_by"], "NEXT_RESERVATION")

    def test_immediate_usage_reports_users_reservation_on_other_computer(self):
        fixed_now = self.aware(self.today, time(8, 21))
        other_computer = Computer.objects.create(code="PC-02")
        create_reservation(
            user_reference="aluno-si-001",
            computer=other_computer,
            starts_at=self.aware(self.today, time(9)),
            ends_at=self.aware(self.today, time(10)),
            created_by_profile="ROOM_USER",
        )

        with patch(
            "apps.operations.availability.timezone.now",
            return_value=fixed_now,
        ):
            response = self.client.get(
                "/api/computers/availability/",
                {"date": self.today.isoformat()},
            )

        item = next(
            computer
            for computer in response.data["computers"]
            if computer["id"] == self.computer.pk
        )
        self.assertEqual(
            item["immediate_usage"]["max_planned_ends_at"],
            self.aware(self.today, time(9)).isoformat(),
        )
        self.assertEqual(item["immediate_usage"]["limited_by"], "USER_RESERVATION")

    def test_immediate_usage_accounts_for_users_allocation_on_other_computer(self):
        fixed_now = self.aware(self.today, time(8, 21))
        other_computer = Computer.objects.create(code="PC-02")
        session = create_use_session(
            user_reference="aluno-si-001",
            started_at=self.aware(self.today, time(8)),
            planned_ends_at=self.aware(self.today, time(9)),
            exit_deadline_at=self.aware(self.today, time(9, 3)),
            entry_recorded_by_profile="ROOM_USER",
        )
        ComputerAllocation.objects.create(
            session=session,
            computer=other_computer,
            sequence=1,
            started_at=self.aware(self.today, time(8)),
        )

        with patch(
            "apps.operations.availability.timezone.now",
            return_value=fixed_now,
        ):
            response = self.client.get(
                "/api/computers/availability/",
                {"date": self.today.isoformat()},
            )

        item = next(
            computer
            for computer in response.data["computers"]
            if computer["id"] == self.computer.pk
        )
        self.assertFalse(item["immediate_usage"]["can_start_now"])
        self.assertEqual(item["immediate_usage"]["limited_by"], "ACTIVE_ALLOCATION")

    def test_checkout_tolerance_affects_current_status_not_future_slots(self):
        fixed_now = self.aware(self.today, time(9, 1))
        session = create_use_session(
            user_reference="another-user",
            started_at=self.aware(self.today, time(8)),
            planned_ends_at=self.aware(self.today, time(9)),
            exit_deadline_at=self.aware(self.today, time(9, 3)),
            entry_recorded_by_profile="ROOM_MONITOR",
        )
        ComputerAllocation.objects.create(
            session=session,
            computer=self.computer,
            sequence=1,
            started_at=self.aware(self.today, time(8)),
        )
        create_reservation(
            user_reference="reserved-user",
            computer=self.computer,
            starts_at=self.aware(self.today, time(9)),
            ends_at=self.aware(self.today, time(10)),
            created_by_profile="ROOM_USER",
        )

        with patch(
            "apps.operations.availability.timezone.now",
            return_value=fixed_now,
        ):
            response = self.client.get(
                "/api/computers/availability/",
                {"date": self.today.isoformat()},
            )
            slots_response = self.client.get(
                f"/api/computers/{self.computer.pk}/slots/",
                {"date": self.today.isoformat()},
            )

        self.assertEqual(
            response.data["computers"][0]["effective_status_now"], "OCCUPIED"
        )
        reservation_slot = next(
            slot
            for slot in slots_response.data["slots"]
            if slot["starts_at"] == self.aware(self.today, time(9)).isoformat()
        )
        self.assertEqual(reservation_slot["effective_status"], "RESERVED")

    def test_closed_calendar_exception_returns_no_slots(self):
        CalendarException.objects.create(
            date=self.tomorrow,
            exception_type=CalendarException.ExceptionType.CLOSED,
            description="Fechamento de demonstração",
        )

        response = self.client.get(
            f"/api/computers/{self.computer.pk}/slots/",
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
                f"/api/computers/{self.computer.pk}/slots/",
                {"date": saturday.date().isoformat()},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["room"]["status"], "OPEN")
        self.assertEqual(response.data["room"]["source"], "REGULAR_SCHEDULE")
        self.assertEqual(len(response.data["slots"]), 23)
        self.assertEqual(
            response.data["slots"][-1]["ends_at"],
            self.aware(saturday.date(), time(13)).isoformat(),
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
                "/api/computers/availability/",
                {"date": sunday_now.date().isoformat()},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["room"]["status"], "CLOSED")
        self.assertIn("domingos", response.data["room"]["reason"])
        self.assertEqual(response.data["computers"][0]["available_slot_count"], 0)
        self.assertFalse(response.data["computers"][0]["can_start_now"])
