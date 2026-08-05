from datetime import datetime, time, timedelta
from unittest.mock import patch

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.audit.models import AuditEvent
from apps.computers.models import Computer
from apps.configuration.models import BookingPolicy, CalendarException, Shift
from apps.operations.models import ComputerAllocation, Reservation, UseSession
from apps.operations.services import start_usage_session


class UsageSessionAPITest(APITestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.current = self.aware(time(8, 0))
        self.computer = Computer.objects.create(code="PC-01")
        self.other_computer = Computer.objects.create(code="PC-02")
        Shift.objects.create(
            name="1º Turno",
            start_time=time(7, 0),
            end_time=time(13, 0),
            valid_from=self.today - timedelta(days=1),
        )
        BookingPolicy.objects.create(
            slot_duration_minutes=60,
            check_in_tolerance_minutes=15,
            max_future_reservations_per_user=2,
            valid_from=self.today - timedelta(days=1),
            is_active=True,
        )
        self.select_room_user()

    def aware(self, value, target_date=None):
        return timezone.make_aware(
            datetime.combine(target_date or self.today, value),
            timezone.get_current_timezone(),
        )

    def select_room_user(
        self,
        reference="aluno-si-001",
        affiliation_type="STUDENT",
        unit="Sistemas de Informação",
    ):
        self.client.post(
            "/api/v1/demo/select-profile/",
            {
                "profile": "ROOM_USER",
                "user_reference": reference,
                "affiliation_type": affiliation_type,
                "institutional_unit": unit,
            },
            format="json",
        )

    def start(self, payload=None, current=None):
        with patch(
            "apps.operations.services.usage_sessions.timezone.now",
            return_value=current or self.current,
        ):
            return self.client.post(
                "/api/v1/usage-sessions/start/",
                payload or {"computer_id": self.computer.pk},
                format="json",
            )

    def test_immediate_entry_creates_session_allocation_and_current_response(self):
        response = self.start()

        self.assertEqual(response.status_code, 201)
        session = UseSession.objects.get()
        allocation = session.allocations.get()
        self.assertEqual(session.user_reference, "aluno-si-001")
        self.assertEqual(session.affiliation_type, "STUDENT")
        self.assertEqual(session.start_shift.name, "1º Turno")
        self.assertEqual(allocation.computer, self.computer)
        self.assertEqual(allocation.sequence, 1)

        current_response = self.client.get("/api/v1/usage-sessions/current/")
        self.assertEqual(current_response.status_code, 200)
        self.assertEqual(current_response.data["id"], session.pk)
        self.assertEqual(len(current_response.data["allocations"]), 1)

    def test_reserved_entry_uses_reservation_snapshots_and_marks_it_used(self):
        reservation = Reservation.objects.create(
            user_reference="aluno-si-001",
            affiliation_type="STUDENT",
            institutional_unit="Sistemas de Informação",
            computer=self.computer,
            starts_at=self.aware(time(8, 0)),
            ends_at=self.aware(time(9, 0)),
            created_by_profile="ROOM_USER",
        )
        self.select_room_user(
            affiliation_type="PROFESSOR",
            unit="Ciência da Computação",
        )

        response = self.start(
            {
                "computer_id": self.computer.pk,
                "reservation_id": reservation.pk,
            },
            current=self.aware(time(7, 50)),
        )

        self.assertEqual(response.status_code, 201)
        session = UseSession.objects.get()
        reservation.refresh_from_db()
        self.assertEqual(session.reservation, reservation)
        self.assertEqual(session.affiliation_type, "STUDENT")
        self.assertEqual(session.institutional_unit, "Sistemas de Informação")
        self.assertEqual(reservation.status, Reservation.Status.USED)

    def test_reserved_entry_rejects_outside_tolerance(self):
        reservation = Reservation.objects.create(
            user_reference="aluno-si-001",
            computer=self.computer,
            starts_at=self.aware(time(9, 0)),
            ends_at=self.aware(time(10, 0)),
            created_by_profile="ROOM_USER",
        )

        response = self.start(
            {
                "computer_id": self.computer.pk,
                "reservation_id": reservation.pk,
            },
            current=self.aware(time(8, 44)),
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "RESERVATION_CHECK_IN_UNAVAILABLE")

    def test_entry_rejects_active_user_occupied_and_maintenance_computer(self):
        self.start()
        duplicate = self.start({"computer_id": self.other_computer.pk})
        occupied = self.start()
        maintenance = Computer.objects.create(
            code="PC-03",
            operational_state=Computer.OperationalState.MAINTENANCE,
        )
        self.select_room_user("aluno-si-002")
        maintenance_response = self.start({"computer_id": maintenance.pk})

        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(occupied.status_code, 409)
        self.assertEqual(maintenance_response.status_code, 409)

    def test_immediate_entry_rejects_closed_room_and_other_users_reservation(self):
        CalendarException.objects.create(
            date=self.today,
            exception_type=CalendarException.ExceptionType.CLOSED,
        )
        closed_response = self.start()
        CalendarException.objects.all().delete()
        Reservation.objects.create(
            user_reference="aluno-si-002",
            computer=self.computer,
            starts_at=self.aware(time(7, 30)),
            ends_at=self.aware(time(8, 30)),
            created_by_profile="ROOM_USER",
        )
        reserved_response = self.start()

        self.assertEqual(closed_response.status_code, 409)
        self.assertEqual(closed_response.data["code"], "ROOM_CLOSED")
        self.assertEqual(reserved_response.status_code, 409)

    def test_operational_entry_requires_and_uses_identity_from_body(self):
        self.client.post(
            "/api/v1/demo/select-profile/",
            {"profile": "INTERN"},
            format="json",
        )
        missing_response = self.start({"computer_id": self.computer.pk})
        valid_response = self.start(
            {
                "computer_id": self.computer.pk,
                "user_reference": "professor-001",
                "affiliation_type": "PROFESSOR",
                "institutional_unit": "Centro de Ciências Exatas",
            }
        )

        self.assertEqual(missing_response.status_code, 400)
        self.assertEqual(valid_response.status_code, 201)
        self.assertEqual(UseSession.objects.get().user_reference, "professor-001")

    def test_special_hours_can_create_session_without_matching_shift(self):
        CalendarException.objects.create(
            date=self.today,
            exception_type=CalendarException.ExceptionType.SPECIAL_HOURS,
            opens_at=time(14, 0),
            closes_at=time(16, 0),
        )

        response = self.start(current=self.aware(time(14, 30)))

        self.assertEqual(response.status_code, 201)
        self.assertIsNone(UseSession.objects.get().start_shift)

    def test_switch_preserves_session_and_increments_allocation_sequence(self):
        self.start()
        session = UseSession.objects.get()

        with patch(
            "apps.operations.services.usage_sessions.timezone.now",
            return_value=self.aware(time(9, 0)),
        ):
            response = self.client.post(
                f"/api/v1/usage-sessions/{session.pk}/switch-computer/",
                {"computer_id": self.other_computer.pk, "reason": "Preferência."},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        allocations = list(session.allocations.order_by("sequence"))
        self.assertEqual(len(allocations), 2)
        self.assertEqual(allocations[0].end_reason, ComputerAllocation.EndReason.SWITCH)
        self.assertEqual(allocations[1].computer, self.other_computer)
        self.assertEqual(allocations[1].sequence, 2)

    def test_switch_rejects_occupied_destination(self):
        self.start()
        session = UseSession.objects.get()
        other_session = UseSession.objects.create(
            user_reference="aluno-si-002",
            entry_recorded_by_profile="ROOM_USER",
        )
        ComputerAllocation.objects.create(
            session=other_session,
            computer=self.other_computer,
            sequence=1,
        )

        response = self.client.post(
            f"/api/v1/usage-sessions/{session.pk}/switch-computer/",
            {"computer_id": self.other_computer.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(session.allocations.count(), 1)

    def test_finish_closes_current_allocation_and_rejects_duplicate(self):
        self.start()
        session = UseSession.objects.get()

        with patch(
            "apps.operations.services.usage_sessions.timezone.now",
            return_value=self.aware(time(10, 0)),
        ):
            response = self.client.post(
                f"/api/v1/usage-sessions/{session.pk}/finish/",
                format="json",
            )
        duplicate = self.client.post(
            f"/api/v1/usage-sessions/{session.pk}/finish/",
            format="json",
        )

        session.refresh_from_db()
        allocation = session.allocations.get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(session.status, UseSession.Status.FINISHED)
        self.assertEqual(
            allocation.end_reason,
            ComputerAllocation.EndReason.SESSION_FINISHED,
        )

    def test_operational_finish_requires_reason_and_creates_audit_event(self):
        self.start()
        session = UseSession.objects.get()
        self.client.post(
            "/api/v1/demo/select-profile/",
            {"profile": "INTERN"},
            format="json",
        )

        missing_response = self.client.post(
            f"/api/v1/usage-sessions/{session.pk}/finish/",
            format="json",
        )
        with patch(
            "apps.operations.services.usage_sessions.timezone.now",
            return_value=self.aware(time(10, 0)),
        ):
            valid_response = self.client.post(
                f"/api/v1/usage-sessions/{session.pk}/finish/",
                {"reason": "Usuário esqueceu de registrar a saída."},
                format="json",
            )

        self.assertEqual(missing_response.status_code, 400)
        self.assertEqual(valid_response.status_code, 200)
        audit_event = AuditEvent.objects.get(action="USAGE_SESSION_FINISHED")
        self.assertEqual(audit_event.entity_id, str(session.pk))

    def test_active_and_history_visibility_follow_profile(self):
        self.start()
        own_session = UseSession.objects.get()
        other_session = UseSession.objects.create(
            user_reference="aluno-si-002",
            started_at=self.current - timedelta(hours=1),
            status=UseSession.Status.FINISHED,
            ended_at=self.current,
            entry_recorded_by_profile="ROOM_USER",
        )

        room_active = self.client.get("/api/v1/usage-sessions/active/")
        room_history = self.client.get("/api/v1/usage-sessions/history/")
        self.client.post(
            "/api/v1/demo/select-profile/",
            {"profile": "INTERN"},
            format="json",
        )
        operational_active = self.client.get("/api/v1/usage-sessions/active/")
        operational_history = self.client.get("/api/v1/usage-sessions/history/")

        self.assertEqual(room_active.status_code, 403)
        self.assertEqual(room_history.data, [])
        self.assertEqual(operational_active.data[0]["id"], own_session.pk)
        self.assertEqual(operational_history.data[0]["id"], other_session.pk)

    def test_entry_rolls_back_when_allocation_creation_fails(self):
        reservation = Reservation.objects.create(
            user_reference="aluno-si-001",
            affiliation_type="STUDENT",
            institutional_unit="Sistemas de Informação",
            computer=self.computer,
            starts_at=self.current,
            ends_at=self.current + timedelta(hours=1),
            created_by_profile="ROOM_USER",
        )
        with (
            patch(
                "apps.operations.services.usage_sessions.ComputerAllocation.objects.create",
                side_effect=RuntimeError("falha intermediária"),
            ),
            self.assertRaises(RuntimeError),
        ):
            start_usage_session(
                computer_id=self.computer.pk,
                reservation_id=reservation.pk,
                actor_profile="ROOM_USER",
                actor_reference="aluno-si-001",
                now=self.current,
            )

        self.assertFalse(UseSession.objects.exists())
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.CONFIRMED)
