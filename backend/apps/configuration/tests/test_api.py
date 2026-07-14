from datetime import time, timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.configuration.models import BookingPolicy, Shift


class ConfigurationAPITest(APITestCase):
    def select_profile(self, profile):
        self.client.post(
            "/api/v1/demo/select-profile/",
            {"profile": profile},
            format="json",
        )

    def test_room_user_can_list_but_cannot_create_shift(self):
        Shift.objects.create(
            name="Manhã",
            start_time=time(7, 0),
            end_time=time(12, 0),
        )
        self.select_profile("ROOM_USER")

        list_response = self.client.get("/api/v1/shifts/")
        create_response = self.client.post(
            "/api/v1/shifts/",
            {
                "name": "Tarde",
                "start_time": "13:00:00",
                "end_time": "17:00:00",
            },
            format="json",
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(create_response.status_code, 403)

    def test_supervisor_can_create_shift(self):
        self.select_profile("LIBRARY_SUPERVISOR")

        response = self.client.post(
            "/api/v1/shifts/",
            {
                "name": "Manhã",
                "start_time": "07:15:00",
                "end_time": "13:00:00",
                "display_order": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Manhã")

    def test_rejects_overlapping_active_shifts(self):
        Shift.objects.create(
            name="Manhã",
            start_time=time(7, 0),
            end_time=time(13, 0),
        )
        self.select_profile("LIBRARY_SUPERVISOR")

        response = self.client.post(
            "/api/v1/shifts/",
            {
                "name": "Sobreposto",
                "start_time": "12:00:00",
                "end_time": "14:00:00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("non_field_errors", response.data["fields"])

    def test_booking_policy_update_preserves_previous_version(self):
        previous_date = timezone.localdate() - timedelta(days=1)
        old_policy = BookingPolicy.objects.create(
            slot_duration_minutes=60,
            valid_from=previous_date,
            is_active=True,
        )
        self.select_profile("LIBRARY_SUPERVISOR")

        response = self.client.patch(
            "/api/v1/booking-policy/",
            {"slot_duration_minutes": 30},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["slot_duration_minutes"], 30)
        old_policy.refresh_from_db()
        self.assertFalse(old_policy.is_active)
        self.assertEqual(BookingPolicy.objects.filter(is_active=True).count(), 1)
