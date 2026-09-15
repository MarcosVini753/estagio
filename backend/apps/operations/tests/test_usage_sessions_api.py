from datetime import date, datetime, time, timedelta
from unittest.mock import patch

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.audit.models import AuditEvent
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
from apps.operations.services import start_usage_session

from .factories import create_reservation, create_use_session


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
        OperatingSchedule.objects.all().delete()
        create_operating_schedule(
            valid_from=self.today - timedelta(days=1),
            weekday_windows={
                weekday: [(time(7), time(13))] for weekday in Weekday.values
            },
        )
        BookingPolicy.objects.create(
            max_future_reservations_per_user=2,
            valid_from=self.today - timedelta(days=1),
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
            "/api/demo/select-profile/",
            {
                "profile": "ROOM_USER",
                "user_reference": reference,
                "affiliation_type": affiliation_type,
                "institutional_unit": unit,
            },
            format="json",
        )

    def immediate_end(self, current, marks=4):
        duration = timedelta(minutes=15)
        anchor = self.aware(time(7, 15), current.date())
        first_end = anchor + ((current - anchor) // duration + 1) * duration
        return first_end + (marks - 1) * duration

    def start(self, payload=None, current=None):
        current = current or self.current
        if payload is None:
            payload = {
                "computer_id": self.computer.pk,
                "planned_ends_at": self.immediate_end(current).isoformat(),
            }
        elif "reservation_id" not in payload and "planned_ends_at" not in payload:
            payload = {
                **payload,
                "planned_ends_at": self.immediate_end(current).isoformat(),
            }
        with patch(
            "apps.operations.services.usage_sessions.timezone.now",
            return_value=current,
        ):
            return self.client.post(
                "/api/usage-sessions/start/",
                payload,
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

        current_response = self.client.get("/api/usage-sessions/current/")
        self.assertEqual(current_response.status_code, 200)
        self.assertEqual(current_response.data["id"], session.pk)
        self.assertEqual(len(current_response.data["allocations"]), 1)

    def test_immediate_entry_uses_selected_grid_end_and_deadline(self):
        current = self.aware(time(8, 21))

        response = self.start(
            {
                "computer_id": self.computer.pk,
                "planned_ends_at": self.aware(time(8, 30)).isoformat(),
            },
            current=current,
        )

        self.assertEqual(response.status_code, 201)
        self.assertNotIn("slot_count", response.data)
        self.assertEqual(response.data["planned_starts_at"], current.isoformat())
        self.assertEqual(
            response.data["planned_ends_at"], self.aware(time(8, 30)).isoformat()
        )
        self.assertEqual(
            response.data["exit_deadline_at"], self.aware(time(8, 33)).isoformat()
        )

    def test_immediate_entry_requires_planned_end_and_rejects_legacy_slot_count(self):
        with patch(
            "apps.operations.services.usage_sessions.timezone.now",
            return_value=self.current,
        ):
            missing = self.client.post(
                "/api/usage-sessions/start/",
                {"computer_id": self.computer.pk},
                format="json",
            )
            legacy = self.client.post(
                "/api/usage-sessions/start/",
                {"computer_id": self.computer.pk, "slot_count": 1},
                format="json",
            )

        self.assertEqual(missing.status_code, 400)
        self.assertEqual(legacy.status_code, 400)
        self.assertFalse(UseSession.objects.exists())

    def test_immediate_entry_rejects_end_outside_the_fixed_grid_without_persisting(
        self,
    ):
        response = self.start(
            {
                "computer_id": self.computer.pk,
                "planned_ends_at": self.aware(time(8, 31)).isoformat(),
            },
            current=self.aware(time(8, 21)),
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "USAGE_SESSION_CONFLICT")
        self.assertFalse(UseSession.objects.exists())

    def test_reserved_entry_uses_reservation_snapshots_and_marks_it_used(self):
        reservation = create_reservation(
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
            current=self.aware(time(8, 0)),
        )

        self.assertEqual(response.status_code, 201)
        session = UseSession.objects.get()
        reservation.refresh_from_db()
        self.assertEqual(session.reservation, reservation)
        self.assertEqual(session.affiliation_type, "STUDENT")
        self.assertEqual(session.institutional_unit, "Sistemas de Informação")
        self.assertEqual(session.planned_starts_at, reservation.starts_at)
        self.assertEqual(session.planned_ends_at, reservation.ends_at)
        self.assertEqual(session.exit_deadline_at, reservation.exit_deadline_at)
        self.assertEqual(reservation.status, Reservation.Status.USED)

    def test_reserved_entry_rejects_planned_end(self):
        reservation = create_reservation(
            user_reference="aluno-si-001",
            computer=self.computer,
            starts_at=self.current,
            ends_at=self.aware(time(9)),
            created_by_profile="ROOM_USER",
        )

        response = self.start(
            {
                "computer_id": self.computer.pk,
                "reservation_id": reservation.pk,
                "planned_ends_at": self.aware(time(9, 30)).isoformat(),
            }
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(UseSession.objects.exists())

    def test_reserved_entry_accepts_exact_check_in_deadline(self):
        reservation = create_reservation(
            user_reference="aluno-si-001",
            computer=self.computer,
            starts_at=self.aware(time(9)),
            ends_at=self.aware(time(10)),
            created_by_profile="ROOM_USER",
        )

        response = self.start(
            {
                "computer_id": self.computer.pk,
                "reservation_id": reservation.pk,
            },
            current=self.aware(time(9, 3)),
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["planned_ends_at"], self.aware(time(10)).isoformat()
        )

    def test_reserved_entry_accepts_exact_early_check_in_tolerance(self):
        reservation = create_reservation(
            user_reference="aluno-si-001",
            computer=self.computer,
            starts_at=self.aware(time(9)),
            ends_at=self.aware(time(10)),
            created_by_profile="ROOM_USER",
        )
        early_check_in = self.aware(time(8, 57))

        response = self.start(
            {
                "computer_id": self.computer.pk,
                "reservation_id": reservation.pk,
            },
            current=early_check_in,
        )

        self.assertEqual(response.status_code, 201)
        session = UseSession.objects.get()
        self.assertEqual(session.started_at, early_check_in)
        self.assertEqual(session.planned_starts_at, reservation.starts_at)
        self.assertEqual(session.allocations.get().started_at, early_check_in)

    def test_reserved_entry_before_early_check_in_tolerance_is_rejected(self):
        reservation = create_reservation(
            user_reference="aluno-si-001",
            computer=self.computer,
            starts_at=self.aware(time(9)),
            ends_at=self.aware(time(10)),
            created_by_profile="ROOM_USER",
        )

        response = self.start(
            {
                "computer_id": self.computer.pk,
                "reservation_id": reservation.pk,
            },
            current=self.aware(time(8, 56, 59)),
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "RESERVATION_CHECK_IN_UNAVAILABLE")
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.CONFIRMED)

    def test_reserved_entry_after_deadline_is_rejected_and_cancelled(self):
        reservation = create_reservation(
            user_reference="aluno-si-001",
            computer=self.computer,
            starts_at=self.aware(time(9)),
            ends_at=self.aware(time(10)),
            created_by_profile="ROOM_USER",
        )
        current = self.aware(time(9, 3, 1))

        response = self.start(
            {
                "computer_id": self.computer.pk,
                "reservation_id": reservation.pk,
            },
            current=current,
        )

        self.assertEqual(response.status_code, 409)
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.CANCELLED)
        self.assertEqual(reservation.cancelled_at, current)
        self.assertEqual(reservation.cancelled_by_profile, "SYSTEM_ADMIN")

    def test_cancelled_reservation_cannot_be_used_for_check_in(self):
        reservation = create_reservation(
            user_reference="aluno-si-001",
            computer=self.computer,
            starts_at=self.aware(time(8)),
            ends_at=self.aware(time(9)),
            status=Reservation.Status.CANCELLED,
            cancelled_by_profile="LIBRARY_SUPERVISOR",
            cancelled_at=self.current - timedelta(hours=1),
            cancellation_reason="Fechamento excepcional.",
            created_by_profile="ROOM_USER",
        )

        response = self.start(
            {
                "computer_id": self.computer.pk,
                "reservation_id": reservation.pk,
            },
            current=self.current,
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
        create_reservation(
            user_reference="aluno-si-002",
            computer=self.computer,
            starts_at=self.aware(time(8, 30)),
            ends_at=self.aware(time(9, 30)),
            created_by_profile="ROOM_USER",
        )
        reserved_response = self.start()

        self.assertEqual(closed_response.status_code, 409)
        self.assertEqual(closed_response.data["code"], "ROOM_CLOSED")
        self.assertEqual(reserved_response.status_code, 409)

    def test_immediate_entry_respects_own_reservation_on_another_computer(self):
        create_reservation(
            user_reference="aluno-si-001",
            computer=self.other_computer,
            starts_at=self.aware(time(8, 30)),
            ends_at=self.aware(time(9, 30)),
            created_by_profile="ROOM_USER",
        )

        response = self.start()

        self.assertEqual(response.status_code, 409)
        self.assertFalse(UseSession.objects.exists())

    def test_immediate_entry_reconciles_overdue_own_reservation_elsewhere(self):
        reservation = create_reservation(
            user_reference="aluno-si-001",
            computer=self.other_computer,
            starts_at=self.aware(time(7, 30)),
            ends_at=self.aware(time(8, 30)),
            created_by_profile="ROOM_USER",
        )

        response = self.start()

        self.assertEqual(response.status_code, 201)
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.CANCELLED)
        self.assertEqual(reservation.cancelled_at, self.current)

    def test_immediate_entry_can_end_when_next_reservation_starts(self):
        reservation = create_reservation(
            user_reference="aluno-si-002",
            computer=self.computer,
            starts_at=self.aware(time(9)),
            ends_at=self.aware(time(10)),
            created_by_profile="ROOM_USER",
        )

        response = self.start()

        self.assertEqual(response.status_code, 201)
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.CONFIRMED)
        self.assertEqual(
            UseSession.objects.get().planned_ends_at,
            reservation.starts_at,
        )

    def test_immediate_entry_may_use_checkout_tolerance_after_closing(self):
        response = self.start(
            {
                "computer_id": self.computer.pk,
                "planned_ends_at": self.aware(time(13)).isoformat(),
            },
            current=self.aware(time(12, 45)),
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["planned_ends_at"], self.aware(time(13)).isoformat()
        )
        self.assertEqual(
            response.data["exit_deadline_at"], self.aware(time(13, 3)).isoformat()
        )

    def test_new_entry_reconciles_users_expired_session_on_other_computer(self):
        expired_session = create_use_session(
            user_reference="aluno-si-002",
            started_at=self.aware(time(8)),
            planned_ends_at=self.aware(time(8, 15)),
            exit_deadline_at=self.aware(time(8, 18)),
            entry_recorded_by_profile="ROOM_USER",
        )
        old_allocation = ComputerAllocation.objects.create(
            session=expired_session,
            computer=self.other_computer,
            sequence=1,
            started_at=self.aware(time(8)),
        )
        self.select_room_user("aluno-si-002")

        response = self.start(
            {
                "computer_id": self.computer.pk,
                "planned_ends_at": self.aware(time(8, 30)).isoformat(),
            },
            current=self.aware(time(8, 18)),
        )

        self.assertEqual(response.status_code, 201)
        expired_session.refresh_from_db()
        old_allocation.refresh_from_db()
        self.assertEqual(expired_session.ended_at, self.aware(time(8, 18)))
        self.assertEqual(
            old_allocation.end_reason,
            ComputerAllocation.EndReason.TIME_LIMIT_REACHED,
        )

    def test_next_reservation_can_enter_when_previous_tolerance_ends(self):
        self.start()
        previous_session = UseSession.objects.get()
        reservation = create_reservation(
            user_reference="aluno-si-002",
            affiliation_type="STUDENT",
            institutional_unit="Sistemas de Informação",
            computer=self.computer,
            starts_at=self.aware(time(9)),
            ends_at=self.aware(time(10)),
            created_by_profile="ROOM_USER",
        )
        self.select_room_user("aluno-si-002")

        response = self.start(
            {
                "computer_id": self.computer.pk,
                "reservation_id": reservation.pk,
            },
            current=self.aware(time(9, 3)),
        )

        self.assertEqual(response.status_code, 201)
        previous_session.refresh_from_db()
        previous_allocation = previous_session.allocations.get()
        reservation.refresh_from_db()
        self.assertEqual(previous_session.ended_at, self.aware(time(9, 3)))
        self.assertEqual(
            previous_allocation.end_reason,
            ComputerAllocation.EndReason.TIME_LIMIT_REACHED,
        )
        self.assertEqual(reservation.status, Reservation.Status.USED)
        self.assertEqual(
            ComputerAllocation.objects.filter(ended_at__isnull=True).count(), 1
        )

    def test_weekend_regular_schedule_controls_immediate_entry(self):
        OperatingSchedule.objects.all().delete()
        create_operating_schedule()
        saturday_before_close = self.aware(time(12, 30), date(2026, 8, 8))

        allowed = self.start(
            {
                "computer_id": self.computer.pk,
                "planned_ends_at": self.aware(time(13), date(2026, 8, 8)).isoformat(),
            },
            current=saturday_before_close,
        )

        self.assertEqual(allowed.status_code, 201)

    def test_saturday_after_13_and_sunday_reject_immediate_entry(self):
        OperatingSchedule.objects.all().delete()
        create_operating_schedule()
        saturday_after_close = self.aware(time(13, 1), date(2026, 8, 8))
        sunday = self.aware(time(8), date(2026, 8, 9))

        saturday_response = self.start(current=saturday_after_close)
        sunday_response = self.start(current=sunday)

        self.assertEqual(saturday_response.status_code, 409)
        self.assertEqual(saturday_response.data["code"], "ROOM_CLOSED")
        self.assertEqual(sunday_response.status_code, 409)
        self.assertEqual(sunday_response.data["code"], "ROOM_CLOSED")

    def test_operational_entry_requires_and_uses_identity_from_body(self):
        self.client.post(
            "/api/demo/select-profile/",
            {"profile": "ROOM_MONITOR"},
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
        planned_end = self.aware(time(9))
        self.start(
            {
                "computer_id": self.computer.pk,
                "planned_ends_at": planned_end.isoformat(),
            }
        )
        session = UseSession.objects.get()
        exit_deadline = session.exit_deadline_at

        with patch(
            "apps.operations.services.usage_sessions.timezone.now",
            return_value=self.aware(time(8, 30)),
        ):
            response = self.client.post(
                f"/api/usage-sessions/{session.pk}/switch-computer/",
                {"computer_id": self.other_computer.pk, "reason": "Preferência."},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        allocations = list(session.allocations.order_by("sequence"))
        self.assertEqual(len(allocations), 2)
        self.assertEqual(allocations[0].end_reason, ComputerAllocation.EndReason.SWITCH)
        self.assertEqual(allocations[1].computer, self.other_computer)
        self.assertEqual(allocations[1].sequence, 2)
        session.refresh_from_db()
        self.assertEqual(session.planned_ends_at, planned_end)
        self.assertEqual(session.exit_deadline_at, exit_deadline)

    def test_switch_preserves_the_interval_inherited_from_a_reservation(self):
        reservation = create_reservation(
            user_reference="aluno-si-001",
            computer=self.computer,
            starts_at=self.current,
            ends_at=self.aware(time(9)),
            created_by_profile="ROOM_USER",
        )
        self.start({"computer_id": self.computer.pk, "reservation_id": reservation.pk})
        session = UseSession.objects.get()
        planned_end = session.planned_ends_at
        exit_deadline = session.exit_deadline_at

        with patch(
            "apps.operations.services.usage_sessions.timezone.now",
            return_value=self.aware(time(8, 30)),
        ):
            response = self.client.post(
                f"/api/usage-sessions/{session.pk}/switch-computer/",
                {"computer_id": self.other_computer.pk},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        session.refresh_from_db()
        self.assertEqual(session.planned_ends_at, planned_end)
        self.assertEqual(session.exit_deadline_at, exit_deadline)

    def test_switch_rejects_occupied_destination(self):
        self.start()
        session = UseSession.objects.get()
        other_session = create_use_session(
            user_reference="aluno-si-002",
            entry_recorded_by_profile="ROOM_USER",
        )
        ComputerAllocation.objects.create(
            session=other_session,
            computer=self.other_computer,
            sequence=1,
        )

        response = self.client.post(
            f"/api/usage-sessions/{session.pk}/switch-computer/",
            {"computer_id": self.other_computer.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(session.allocations.count(), 1)

    def test_switch_checks_destination_for_entire_remaining_interval(self):
        self.start()
        session = UseSession.objects.get()
        create_reservation(
            user_reference="aluno-si-002",
            computer=self.other_computer,
            starts_at=self.aware(time(8, 45)),
            ends_at=self.aware(time(9, 45)),
            created_by_profile="ROOM_USER",
        )

        with patch(
            "apps.operations.services.usage_sessions.timezone.now",
            return_value=self.aware(time(8, 30)),
        ):
            response = self.client.post(
                f"/api/usage-sessions/{session.pk}/switch-computer/",
                {"computer_id": self.other_computer.pk},
                format="json",
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(session.allocations.count(), 1)

    def test_switch_is_rejected_during_checkout_tolerance(self):
        self.start()
        session = UseSession.objects.get()

        with patch(
            "apps.operations.services.usage_sessions.timezone.now",
            return_value=self.aware(time(9)),
        ):
            response = self.client.post(
                f"/api/usage-sessions/{session.pk}/switch-computer/",
                {"computer_id": self.other_computer.pk},
                format="json",
            )

        self.assertEqual(response.status_code, 409)
        self.assertIn("tempo planejado restante", response.data["detail"])
        self.assertNotIn("tolerância", response.data["detail"].lower())
        self.assertEqual(session.allocations.count(), 1)

    def test_switch_reconciles_session_at_its_exit_deadline(self):
        self.start()
        session = UseSession.objects.get()

        with patch(
            "apps.operations.services.usage_sessions.timezone.now",
            return_value=self.aware(time(9, 3)),
        ):
            response = self.client.post(
                f"/api/usage-sessions/{session.pk}/switch-computer/",
                {"computer_id": self.other_computer.pk},
                format="json",
            )

        self.assertEqual(response.status_code, 409)
        session.refresh_from_db()
        allocation = session.allocations.get()
        self.assertEqual(session.ended_at, self.aware(time(9, 3)))
        self.assertEqual(
            allocation.end_reason,
            ComputerAllocation.EndReason.TIME_LIMIT_REACHED,
        )

    def test_finish_closes_current_allocation_and_rejects_duplicate(self):
        self.start()
        session = UseSession.objects.get()

        with patch(
            "apps.operations.services.usage_sessions.timezone.now",
            return_value=self.aware(time(8, 30)),
        ):
            response = self.client.post(
                f"/api/usage-sessions/{session.pk}/finish/",
                format="json",
            )
        duplicate = self.client.post(
            f"/api/usage-sessions/{session.pk}/finish/",
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

    def test_finish_at_exit_deadline_is_accepted(self):
        self.start()
        session = UseSession.objects.get()

        with patch(
            "apps.operations.services.usage_sessions.timezone.now",
            return_value=self.aware(time(9, 3)),
        ):
            response = self.client.post(
                f"/api/usage-sessions/{session.pk}/finish/",
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        session.refresh_from_db()
        self.assertEqual(session.ended_at, self.aware(time(9, 3)))

    def test_operational_finish_requires_reason_and_creates_audit_event(self):
        self.start()
        session = UseSession.objects.get()
        self.client.post(
            "/api/demo/select-profile/",
            {"profile": "ROOM_MONITOR"},
            format="json",
        )

        with patch(
            "apps.operations.services.usage_sessions.timezone.now",
            return_value=self.aware(time(8, 30)),
        ):
            missing_response = self.client.post(
                f"/api/usage-sessions/{session.pk}/finish/",
                format="json",
            )
        with patch(
            "apps.operations.services.usage_sessions.timezone.now",
            return_value=self.aware(time(8, 30)),
        ):
            valid_response = self.client.post(
                f"/api/usage-sessions/{session.pk}/finish/",
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
        other_session = create_use_session(
            user_reference="aluno-si-002",
            started_at=self.current - timedelta(hours=1),
            status=UseSession.Status.FINISHED,
            ended_at=self.current,
            entry_recorded_by_profile="ROOM_USER",
        )

        room_active = self.client.get("/api/usage-sessions/active/")
        room_history = self.client.get("/api/usage-sessions/history/")
        self.client.post(
            "/api/demo/select-profile/",
            {"profile": "ROOM_MONITOR"},
            format="json",
        )
        operational_active = self.client.get("/api/usage-sessions/active/")
        operational_history = self.client.get("/api/usage-sessions/history/")

        self.assertEqual(room_active.status_code, 403)
        self.assertEqual(room_history.data["results"], [])
        self.assertEqual(operational_active.data[0]["id"], own_session.pk)
        self.assertEqual(operational_history.data["results"][0]["id"], other_session.pk)

    def test_history_is_paginated_and_ordered_from_newest(self):
        sessions = []
        for index in range(26):
            started_at = self.current - timedelta(days=index + 1)
            sessions.append(
                create_use_session(
                    user_reference="aluno-si-001",
                    started_at=started_at,
                    ended_at=started_at + timedelta(minutes=15),
                    status=UseSession.Status.FINISHED,
                    entry_recorded_by_profile="ROOM_USER",
                    exit_recorded_by_profile="ROOM_USER",
                )
            )

        first_page = self.client.get("/api/usage-sessions/history/")
        second_page = self.client.get("/api/usage-sessions/history/?page=2")

        self.assertEqual(first_page.data["count"], 26)
        self.assertEqual(len(first_page.data["results"]), 25)
        self.assertEqual(first_page.data["results"][0]["id"], sessions[0].pk)
        self.assertEqual(len(second_page.data["results"]), 1)

    def test_entry_rolls_back_when_allocation_creation_fails(self):
        reservation = create_reservation(
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
