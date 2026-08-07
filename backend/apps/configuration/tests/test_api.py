from datetime import time, timedelta
from unittest.mock import patch

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.audit.models import AuditEvent
from apps.computers.models import Computer
from apps.configuration.models import BookingPolicy, Shift
from apps.configuration.selectors import get_shifts_for_date
from apps.configuration.services import replace_shift
from apps.operations.models import UseSession
from apps.operations.tests.factories import create_reservation, create_use_session


class ConfigurationAPITest(APITestCase):
    def select_profile(self, profile):
        payload = {"profile": profile}
        if profile == "ROOM_USER":
            payload.update(
                {
                    "user_reference": "aluno-si-001",
                    "affiliation_type": "STUDENT",
                    "institutional_unit": "Sistemas de Informação",
                }
            )
        self.client.post(
            "/api/demo/select-profile/",
            payload,
            format="json",
        )

    def test_room_user_can_list_but_cannot_create_shift(self):
        Shift.objects.create(
            name="Manhã",
            start_time=time(7, 0),
            end_time=time(12, 0),
        )
        self.select_profile("ROOM_USER")

        list_response = self.client.get("/api/shifts/")
        create_response = self.client.post(
            "/api/shifts/",
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
            "/api/shifts/",
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
            "/api/shifts/",
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
            valid_from=previous_date,
        )
        self.select_profile("LIBRARY_SUPERVISOR")

        response = self.client.patch(
            "/api/booking-policy/",
            {"cancellation_limit_minutes": 30},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["cancellation_limit_minutes"], 30)
        old_policy.refresh_from_db()
        self.assertEqual(
            old_policy.valid_until, timezone.localdate() - timedelta(days=1)
        )
        self.assertEqual(
            BookingPolicy.objects.filter(valid_until__isnull=True).count(), 1
        )

    def test_booking_policy_referenced_today_is_not_changed_retroactively(self):
        today = timezone.localdate()
        original = BookingPolicy.objects.create(
            cancellation_limit_minutes=15,
            valid_from=today,
        )
        starts_at = timezone.now() + timedelta(days=1)
        reservation = create_reservation(
            user_reference="aluno-politica-historica",
            computer=Computer.objects.create(code="PC-POLICY-HISTORY"),
            starts_at=starts_at,
            ends_at=starts_at + timedelta(minutes=15),
            booking_policy=original,
            created_by_profile="ROOM_USER",
        )
        self.select_profile("LIBRARY_SUPERVISOR")

        response = self.client.patch(
            "/api/booking-policy/",
            {"cancellation_limit_minutes": 30},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        original.refresh_from_db()
        reservation.refresh_from_db()
        self.assertEqual(original.cancellation_limit_minutes, 15)
        self.assertEqual(original.valid_until, today)
        self.assertEqual(reservation.booking_policy, original)
        self.assertEqual(
            response.data["valid_from"], (today + timedelta(days=1)).isoformat()
        )
        self.assertEqual(response.data["cancellation_limit_minutes"], 30)

    def test_booking_policy_does_not_expose_fixed_slot_or_tolerance_rules(self):
        BookingPolicy.objects.create()
        self.select_profile("LIBRARY_SUPERVISOR")

        read_response = self.client.get("/api/booking-policy/")
        update_response = self.client.patch(
            "/api/booking-policy/",
            {
                "slot_duration_minutes": 60,
                "check_in_tolerance_minutes": 15,
            },
            format="json",
        )

        self.assertEqual(read_response.status_code, 200)
        self.assertNotIn("slot_duration_minutes", read_response.data)
        self.assertNotIn("check_in_tolerance_minutes", read_response.data)
        self.assertEqual(update_response.status_code, 400)

    def test_replace_preserves_historical_shift_reference(self):
        today = timezone.localdate()
        shift = Shift.objects.create(
            name="Manhã",
            start_time=time(7, 0),
            end_time=time(12, 0),
            valid_from=today - timedelta(days=7),
        )
        session = create_use_session(
            user_reference="aluno-historico",
            start_shift=shift,
            started_at=timezone.now() - timedelta(days=1),
            ended_at=timezone.now() - timedelta(hours=23),
            status=UseSession.Status.FINISHED,
            entry_recorded_by_profile="ROOM_USER",
        )
        effective_from = today + timedelta(days=1)
        self.select_profile("LIBRARY_SUPERVISOR")

        response = self.client.post(
            f"/api/shifts/{shift.pk}/replace/",
            {
                "effective_from": effective_from.isoformat(),
                "name": "1º Turno",
                "start_time": "08:00:00",
                "end_time": "13:00:00",
                "display_order": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        shift.refresh_from_db()
        session.refresh_from_db()
        self.assertEqual(response.data["series_key"], str(shift.series_key))
        self.assertEqual(shift.valid_until, effective_from - timedelta(days=1))
        self.assertEqual(session.start_shift_id, shift.pk)
        self.assertEqual(get_shifts_for_date(today).get().pk, shift.pk)
        self.assertEqual(
            get_shifts_for_date(effective_from).get().pk, response.data["id"]
        )
        audit_event = AuditEvent.objects.get(action="SHIFT_REPLACED")
        self.assertEqual(audit_event.actor_profile, "LIBRARY_SUPERVISOR")
        self.assertEqual(audit_event.new_values["shift_id"], response.data["id"])

    def test_used_shift_rejects_direct_time_change_but_can_be_deactivated(self):
        shift = Shift.objects.create(
            name="Manhã",
            start_time=time(7, 0),
            end_time=time(12, 0),
        )
        create_use_session(
            user_reference="aluno-historico",
            start_shift=shift,
            status=UseSession.Status.FINISHED,
            entry_recorded_by_profile="ROOM_USER",
        )
        self.select_profile("LIBRARY_SUPERVISOR")

        time_response = self.client.patch(
            f"/api/shifts/{shift.pk}/",
            {"start_time": "08:00:00"},
            format="json",
        )
        deactivate_response = self.client.patch(
            f"/api/shifts/{shift.pk}/",
            {"is_active": False},
            format="json",
        )

        self.assertEqual(time_response.status_code, 400)
        self.assertEqual(deactivate_response.status_code, 200)
        self.assertFalse(deactivate_response.data["is_active"])

    def test_future_unused_shift_keeps_patch_behavior(self):
        shift = Shift.objects.create(
            name="Manhã",
            start_time=time(7, 0),
            end_time=time(12, 0),
            valid_from=timezone.localdate() + timedelta(days=1),
        )
        self.select_profile("LIBRARY_SUPERVISOR")

        response = self.client.patch(
            f"/api/shifts/{shift.pk}/",
            {"start_time": "08:00:00"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["start_time"], "08:00:00")

    def test_replace_rejects_conflicting_active_shift(self):
        today = timezone.localdate()
        shift = Shift.objects.create(
            name="Manhã",
            start_time=time(7, 0),
            end_time=time(12, 0),
            valid_from=today - timedelta(days=1),
        )
        Shift.objects.create(
            name="Conflitante",
            start_time=time(9, 0),
            end_time=time(14, 0),
            valid_from=today + timedelta(days=1),
        )
        self.select_profile("LIBRARY_SUPERVISOR")

        response = self.client.post(
            f"/api/shifts/{shift.pk}/replace/",
            {
                "effective_from": (today + timedelta(days=1)).isoformat(),
                "name": "Novo turno",
                "start_time": "08:00:00",
                "end_time": "13:00:00",
                "display_order": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        shift.refresh_from_db()
        self.assertIsNone(shift.valid_until)
        self.assertEqual(Shift.objects.count(), 2)

    def test_replace_requires_a_future_effective_date(self):
        shift = Shift.objects.create(
            name="Manhã",
            start_time=time(7, 0),
            end_time=time(12, 0),
        )
        self.select_profile("LIBRARY_SUPERVISOR")

        response = self.client.post(
            f"/api/shifts/{shift.pk}/replace/",
            {
                "effective_from": timezone.localdate().isoformat(),
                "name": "Novo turno",
                "start_time": "08:00:00",
                "end_time": "13:00:00",
                "display_order": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("effective_from", response.data["fields"])

    def test_replace_requires_date_after_current_version_start(self):
        effective_from = timezone.localdate() + timedelta(days=1)
        shift = Shift.objects.create(
            name="Manhã",
            start_time=time(7, 0),
            end_time=time(12, 0),
            valid_from=effective_from,
        )
        self.select_profile("LIBRARY_SUPERVISOR")

        response = self.client.post(
            f"/api/shifts/{shift.pk}/replace/",
            {
                "effective_from": effective_from.isoformat(),
                "name": "Novo turno",
                "start_time": "08:00:00",
                "end_time": "13:00:00",
                "display_order": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "SHIFT_REPLACEMENT_INVALID")

    def test_replace_rolls_back_when_audit_fails(self):
        shift = Shift.objects.create(
            name="Manhã",
            start_time=time(7, 0),
            end_time=time(12, 0),
        )

        with (
            patch(
                "apps.configuration.services.AuditEvent.objects.create",
                side_effect=RuntimeError("audit unavailable"),
            ),
            self.assertRaises(RuntimeError),
        ):
            replace_shift(
                shift_id=shift.pk,
                effective_from=timezone.localdate() + timedelta(days=1),
                name="Novo turno",
                start_time=time(8, 0),
                end_time=time(13, 0),
                display_order=1,
                actor_profile="LIBRARY_SUPERVISOR",
            )

        shift.refresh_from_db()
        self.assertIsNone(shift.valid_until)
        self.assertEqual(Shift.objects.count(), 1)
