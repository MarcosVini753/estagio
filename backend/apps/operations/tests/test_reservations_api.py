from datetime import date, datetime, time, timedelta
from unittest.mock import patch

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.audit.models import AuditEvent
from apps.computers.models import Computer
from apps.configuration.models import BookingPolicy, OperatingSchedule, Shift, Weekday
from apps.configuration.tests.factories import create_operating_schedule
from apps.operations.models import ComputerAllocation, Reservation
from apps.operations.services import invalidate_reservation_due_to_calendar_change

from .factories import create_reservation, create_use_session


class ReservationAPITest(APITestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.tomorrow = self.today + timedelta(days=1)
        self.computer = Computer.objects.create(code="PC-01")
        self.other_computer = Computer.objects.create(code="PC-02")
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
            max_future_reservations_per_user=2,
            valid_from=self.today - timedelta(days=1),
            is_active=True,
        )
        self.select_room_user("aluno-si-001")

    def aware(self, target_date, target_time):
        return timezone.make_aware(
            datetime.combine(target_date, target_time),
            timezone.get_current_timezone(),
        )

    def select_room_user(self, reference):
        self.client.post(
            "/api/demo/select-profile/",
            {
                "profile": "ROOM_USER",
                "user_reference": reference,
                "affiliation_type": "STUDENT",
                "institutional_unit": "Sistemas de Informação",
            },
            format="json",
        )

    def create_payload(self, computer=None, starts_at=None, slot_count=4):
        return {
            "computer_id": (computer or self.computer).pk,
            "starts_at": (
                starts_at or self.aware(self.tomorrow, time(8, 0))
            ).isoformat(),
            "slot_count": slot_count,
        }

    def test_room_user_creates_slot_reservation_with_snapshots(self):
        response = self.client.post(
            "/api/reservations/",
            self.create_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "CONFIRMED")
        self.assertEqual(
            response.data["ends_at"], self.aware(self.tomorrow, time(9, 0)).isoformat()
        )
        self.assertEqual(response.data["slot_count"], 4)
        self.assertEqual(
            response.data["check_in_deadline_at"],
            self.aware(self.tomorrow, time(8, 3)).isoformat(),
        )
        self.assertEqual(
            response.data["exit_deadline_at"],
            self.aware(self.tomorrow, time(9, 3)).isoformat(),
        )
        reservation = Reservation.objects.get()
        self.assertEqual(reservation.user_reference, "aluno-si-001")
        self.assertEqual(reservation.affiliation_type, "STUDENT")
        self.assertEqual(reservation.institutional_unit, "Sistemas de Informação")

    def test_operational_profile_cannot_create_reservation(self):
        self.client.post(
            "/api/demo/select-profile/",
            {"profile": "INTERN"},
            format="json",
        )

        response = self.client.post(
            "/api/reservations/",
            self.create_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_room_user_cannot_list_all_reservations(self):
        response = self.client.get("/api/reservations/")

        self.assertEqual(response.status_code, 403)

    def test_rejects_computer_conflict(self):
        create_reservation(
            user_reference="another-user",
            computer=self.computer,
            starts_at=self.aware(self.tomorrow, time(8, 0)),
            ends_at=self.aware(self.tomorrow, time(9, 0)),
            created_by_profile="ROOM_USER",
        )

        response = self.client.post(
            "/api/reservations/",
            self.create_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 409)

    def test_rejects_user_conflict(self):
        create_reservation(
            user_reference="aluno-si-001",
            computer=self.other_computer,
            starts_at=self.aware(self.tomorrow, time(8, 0)),
            ends_at=self.aware(self.tomorrow, time(9, 0)),
            created_by_profile="ROOM_USER",
        )

        response = self.client.post(
            "/api/reservations/",
            self.create_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 409)

    def test_rejects_non_slot_and_date_after_tomorrow(self):
        non_slot_response = self.client.post(
            "/api/reservations/",
            self.create_payload(starts_at=self.aware(self.tomorrow, time(8, 31))),
            format="json",
        )
        later_response = self.client.post(
            "/api/reservations/",
            self.create_payload(
                starts_at=self.aware(self.today + timedelta(days=2), time(8, 0))
            ),
            format="json",
        )

        self.assertEqual(non_slot_response.status_code, 400)
        self.assertEqual(later_response.status_code, 400)
        self.assertEqual(later_response.data["code"], "DATE_OUTSIDE_ALLOWED_WINDOW")

    def test_rejects_zero_slots_without_persisting_reservation(self):
        response = self.client.post(
            "/api/reservations/",
            self.create_payload(slot_count=0),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Reservation.objects.exists())

    def test_rejects_interval_that_crosses_room_closing(self):
        response = self.client.post(
            "/api/reservations/",
            self.create_payload(
                starts_at=self.aware(self.tomorrow, time(9, 15)),
                slot_count=4,
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "RESERVATION_SLOT_INVALID")
        self.assertFalse(Reservation.objects.exists())

    def test_full_interval_conflicts_but_adjacent_interval_is_accepted(self):
        create_reservation(
            user_reference="another-user",
            computer=self.computer,
            starts_at=self.aware(self.tomorrow, time(9)),
            ends_at=self.aware(self.tomorrow, time(10)),
            created_by_profile="ROOM_USER",
        )

        overlapping = self.client.post(
            "/api/reservations/",
            self.create_payload(
                starts_at=self.aware(self.tomorrow, time(8, 15)),
                slot_count=4,
            ),
            format="json",
        )
        adjacent = self.client.post(
            "/api/reservations/",
            self.create_payload(
                starts_at=self.aware(self.tomorrow, time(8)),
                slot_count=4,
            ),
            format="json",
        )

        self.assertEqual(overlapping.status_code, 409)
        self.assertEqual(adjacent.status_code, 201)
        self.assertEqual(
            adjacent.data["ends_at"], self.aware(self.tomorrow, time(9)).isoformat()
        )

    def test_reservation_rejects_planned_session_of_computer_or_user(self):
        fixed_now = self.aware(self.today, time(8))
        computer_session = create_use_session(
            user_reference="another-user",
            started_at=fixed_now,
            planned_ends_at=self.aware(self.today, time(9)),
            exit_deadline_at=self.aware(self.today, time(9, 3)),
            entry_recorded_by_profile="ROOM_USER",
        )
        ComputerAllocation.objects.create(
            session=computer_session,
            computer=self.computer,
            sequence=1,
            started_at=fixed_now,
        )

        with patch(
            "apps.operations.services.reservations.timezone.now",
            return_value=fixed_now,
        ):
            computer_conflict = self.client.post(
                "/api/reservations/",
                self.create_payload(
                    starts_at=self.aware(self.today, time(8, 30)),
                    slot_count=2,
                ),
                format="json",
            )

        computer_session.status = "FINISHED"
        computer_session.ended_at = self.aware(self.today, time(8, 15))
        computer_session.save(update_fields=["status", "ended_at", "updated_at"])
        allocation = computer_session.allocations.get()
        allocation.ended_at = self.aware(self.today, time(8, 15))
        allocation.save(update_fields=["ended_at", "updated_at"])
        user_session = create_use_session(
            user_reference="aluno-si-001",
            started_at=fixed_now,
            planned_ends_at=self.aware(self.today, time(9)),
            exit_deadline_at=self.aware(self.today, time(9, 3)),
            entry_recorded_by_profile="ROOM_USER",
        )
        ComputerAllocation.objects.create(
            session=user_session,
            computer=self.other_computer,
            sequence=1,
            started_at=fixed_now,
        )

        with patch(
            "apps.operations.services.reservations.timezone.now",
            return_value=fixed_now,
        ):
            user_conflict = self.client.post(
                "/api/reservations/",
                self.create_payload(
                    starts_at=self.aware(self.today, time(8, 30)),
                    slot_count=2,
                ),
                format="json",
            )

        self.assertEqual(computer_conflict.status_code, 409)
        self.assertEqual(user_conflict.status_code, 409)

    def test_rejects_maintenance_computer_and_future_limit(self):
        self.computer.operational_state = Computer.OperationalState.MAINTENANCE
        self.computer.save(update_fields=["operational_state", "updated_at"])
        maintenance_response = self.client.post(
            "/api/reservations/",
            self.create_payload(),
            format="json",
        )
        self.computer.operational_state = Computer.OperationalState.AVAILABLE
        self.computer.save(update_fields=["operational_state", "updated_at"])
        policy = BookingPolicy.objects.get()
        policy.max_future_reservations_per_user = 1
        policy.save(update_fields=["max_future_reservations_per_user", "updated_at"])
        create_reservation(
            user_reference="aluno-si-001",
            computer=self.computer,
            starts_at=self.aware(self.tomorrow, time(7, 0)),
            ends_at=self.aware(self.tomorrow, time(8, 0)),
            created_by_profile="ROOM_USER",
        )

        limit_response = self.client.post(
            "/api/reservations/",
            self.create_payload(),
            format="json",
        )

        self.assertEqual(maintenance_response.status_code, 409)
        self.assertEqual(limit_response.status_code, 409)
        self.assertEqual(limit_response.data["code"], "RESERVATION_LIMIT_REACHED")

    def test_today_reservation_must_start_in_the_future(self):
        fixed_now = self.aware(self.today, time(7, 30))

        with patch(
            "apps.operations.services.reservations.timezone.now",
            return_value=fixed_now,
        ):
            valid_response = self.client.post(
                "/api/reservations/",
                self.create_payload(starts_at=self.aware(self.today, time(8, 0))),
                format="json",
            )
            past_response = self.client.post(
                "/api/reservations/",
                self.create_payload(starts_at=self.aware(self.today, time(7, 0))),
                format="json",
            )

        self.assertEqual(valid_response.status_code, 201)
        self.assertEqual(past_response.status_code, 400)

    def test_weekend_reservations_respect_regular_schedule(self):
        OperatingSchedule.objects.all().delete()
        create_operating_schedule()
        friday = self.aware(date(2026, 8, 7), time(12))
        saturday = date(2026, 8, 8)

        with patch(
            "apps.operations.services.reservations.timezone.now",
            return_value=friday,
        ):
            before_close = self.client.post(
                "/api/reservations/",
                self.create_payload(starts_at=self.aware(saturday, time(11, 15))),
                format="json",
            )
            after_close = self.client.post(
                "/api/reservations/",
                self.create_payload(starts_at=self.aware(saturday, time(14))),
                format="json",
            )

        self.assertEqual(before_close.status_code, 201)
        self.assertEqual(after_close.status_code, 400)

    def test_sunday_reservation_is_rejected(self):
        OperatingSchedule.objects.all().delete()
        create_operating_schedule()
        saturday = self.aware(date(2026, 8, 8), time(12))
        sunday = date(2026, 8, 9)

        with patch(
            "apps.operations.services.reservations.timezone.now",
            return_value=saturday,
        ):
            response = self.client.post(
                "/api/reservations/",
                self.create_payload(starts_at=self.aware(sunday, time(8))),
                format="json",
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "RESERVATION_SLOT_INVALID")

    def test_cancellation_releases_slot_and_is_listed_as_mine(self):
        reservation = create_reservation(
            user_reference="aluno-si-001",
            computer=self.computer,
            starts_at=self.aware(self.tomorrow, time(8, 0)),
            ends_at=self.aware(self.tomorrow, time(9, 0)),
            created_by_profile="ROOM_USER",
        )

        cancel_response = self.client.post(
            f"/api/reservations/{reservation.pk}/cancel/",
            format="json",
        )
        list_response = self.client.get("/api/reservations/mine/")

        self.assertEqual(cancel_response.status_code, 200)
        self.assertEqual(cancel_response.data["status"], "CANCELLED")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data[0]["status"], "CANCELLED")

        replacement_response = self.client.post(
            "/api/reservations/",
            self.create_payload(),
            format="json",
        )
        self.assertEqual(replacement_response.status_code, 201)

    def test_calendar_invalidation_releases_slot_and_keeps_reason_in_mine(self):
        reservation = create_reservation(
            user_reference="aluno-si-001",
            computer=self.computer,
            starts_at=self.aware(self.tomorrow, time(8)),
            ends_at=self.aware(self.tomorrow, time(9)),
            created_by_profile="ROOM_USER",
        )
        invalidate_reservation_due_to_calendar_change(
            reservation_id=reservation.pk,
            actor_profile="LIBRARY_SUPERVISOR",
            reason="Horário reduzido durante o recesso.",
        )

        slots_response = self.client.get(
            f"/api/computers/{self.computer.pk}/slots/",
            {"date": self.tomorrow.isoformat()},
        )
        mine_response = self.client.get("/api/reservations/mine/")

        slot = next(
            item
            for item in slots_response.data["slots"]
            if item["starts_at"] == self.aware(self.tomorrow, time(8)).isoformat()
        )
        self.assertTrue(slot["selectable"])
        self.assertEqual(mine_response.data[0]["status"], "INVALIDATED")
        self.assertEqual(
            mine_response.data[0]["invalidation_reason"],
            "Horário reduzido durante o recesso.",
        )

    def test_other_room_user_cannot_cancel_reservation(self):
        reservation = create_reservation(
            user_reference="aluno-si-001",
            computer=self.computer,
            starts_at=self.aware(self.tomorrow, time(8, 0)),
            ends_at=self.aware(self.tomorrow, time(9, 0)),
            created_by_profile="ROOM_USER",
        )
        self.select_room_user("aluno-si-002")

        response = self.client.post(
            f"/api/reservations/{reservation.pk}/cancel/",
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_operational_profile_can_cancel_another_users_reservation(self):
        reservation = create_reservation(
            user_reference="aluno-si-001",
            computer=self.computer,
            starts_at=self.aware(self.tomorrow, time(8, 0)),
            ends_at=self.aware(self.tomorrow, time(9, 0)),
            created_by_profile="ROOM_USER",
        )
        self.client.post(
            "/api/demo/select-profile/",
            {"profile": "INTERN"},
            format="json",
        )

        response = self.client.post(
            f"/api/reservations/{reservation.pk}/cancel/",
            {"reason": "Solicitação da supervisão."},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["cancelled_by_profile"], "INTERN")
        audit_event = AuditEvent.objects.get(action="RESERVATION_CANCELLED")
        self.assertEqual(audit_event.entity_id, str(reservation.pk))
        self.assertEqual(audit_event.reason, "Solicitação da supervisão.")

    def test_operational_cancellation_requires_reason(self):
        reservation = create_reservation(
            user_reference="aluno-si-001",
            computer=self.computer,
            starts_at=self.aware(self.tomorrow, time(8, 0)),
            ends_at=self.aware(self.tomorrow, time(9, 0)),
            created_by_profile="ROOM_USER",
        )
        self.client.post(
            "/api/demo/select-profile/",
            {"profile": "INTERN"},
            format="json",
        )

        response = self.client.post(
            f"/api/reservations/{reservation.pk}/cancel/",
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["code"], "RESERVATION_CANCELLATION_REASON_REQUIRED"
        )

    def test_cancellation_respects_policy_limit_and_start(self):
        policy = BookingPolicy.objects.get()
        policy.cancellation_limit_minutes = 30
        policy.save(update_fields=["cancellation_limit_minutes", "updated_at"])
        reservation = create_reservation(
            user_reference="aluno-si-001",
            computer=self.computer,
            starts_at=self.aware(self.tomorrow, time(8, 0)),
            ends_at=self.aware(self.tomorrow, time(9, 0)),
            created_by_profile="ROOM_USER",
        )

        with patch(
            "apps.operations.services.reservations.timezone.now",
            return_value=self.aware(self.tomorrow, time(7, 31)),
        ):
            response = self.client.post(
                f"/api/reservations/{reservation.pk}/cancel/",
                format="json",
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "RESERVATION_CANCELLATION_UNAVAILABLE")
