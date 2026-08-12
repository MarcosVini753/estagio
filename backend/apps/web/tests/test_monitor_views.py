from datetime import datetime, time, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.computers.models import Computer
from apps.configuration.models import OperatingSchedule, Weekday
from apps.configuration.tests.factories import create_operating_schedule
from apps.occurrences.models import Occurrence
from apps.operations.models import ComputerAllocation, UseSession
from apps.operations.tests.factories import create_use_session


class RoomMonitorWebTest(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.computer = Computer.objects.create(
            code="PC-01",
            description="Computador próximo à entrada",
        )
        self.other_computer = Computer.objects.create(
            code="PC-02",
            description="Computador de apoio",
        )
        OperatingSchedule.objects.all().delete()
        create_operating_schedule(
            valid_from=self.today - timedelta(days=1),
            weekday_windows={
                weekday: [(time(7), time(22))] for weekday in Weekday.values
            },
        )

    def aware(self, target_time):
        return timezone.make_aware(
            datetime.combine(self.today, target_time),
            timezone.get_current_timezone(),
        )

    def select_monitor(self):
        response = self.client.post("/", {"profile": "ROOM_MONITOR"})
        self.assertRedirects(response, "/monitor/")

    def create_session(self, *, active=True):
        started_at = self.aware(time(8))
        ended_at = None if active else self.aware(time(8, 45))
        session = create_use_session(
            user_reference="aluno-si-001",
            started_at=started_at,
            planned_starts_at=started_at,
            planned_ends_at=self.aware(time(9)),
            exit_deadline_at=self.aware(time(9, 10)),
            ended_at=ended_at,
            status=(UseSession.Status.ACTIVE if active else UseSession.Status.FINISHED),
            entry_recorded_by_profile="ROOM_MONITOR",
            exit_recorded_by_profile="ROOM_MONITOR" if not active else "",
        )
        ComputerAllocation.objects.create(
            session=session,
            computer=self.computer,
            sequence=1,
            started_at=started_at,
            ended_at=ended_at,
            end_reason=(
                ComputerAllocation.EndReason.SESSION_FINISHED if not active else ""
            ),
        )
        return session

    def test_monitor_routes_require_an_operational_profile(self):
        anonymous = self.client.get("/monitor/")

        self.assertRedirects(anonymous, "/")

        self.client.post(
            "/",
            {
                "profile": "ROOM_USER",
                "user_reference": "aluno-si-001",
                "affiliation_type": "STUDENT",
                "institutional_unit": "Sistemas de Informação",
            },
        )
        incompatible = self.client.get("/monitor/")

        self.assertRedirects(incompatible, "/")

    def test_dashboard_lists_active_sessions_and_operating_context(self):
        session = self.create_session()
        self.select_monitor()

        response = self.client.get("/monitor/")
        partial = self.client.get(
            "/monitor/",
            HTTP_HX_REQUEST="true",
            HTTP_HX_TARGET="staff-content",
        )

        self.assertContains(response, "Sessões ativas")
        self.assertContains(response, session.user_reference)
        self.assertContains(response, self.computer.code)
        self.assertContains(response, "Funcionamento de hoje")
        self.assertContains(response, "Autorização simulada")
        self.assertContains(partial, 'id="staff-content"')
        self.assertNotContains(partial, "<!doctype html>")

    def test_changing_computer_state_exposes_session_and_reservation_impact(self):
        session = self.create_session()
        self.select_monitor()

        with patch(
            "apps.operations.services.computer_state.timezone.now",
            return_value=self.aware(time(8, 15)),
        ):
            response = self.client.post(
                f"/monitor/computadores/{self.computer.pk}/estado/",
                {
                    "operational_state": Computer.OperationalState.MAINTENANCE,
                    "reason": "Falha no monitor",
                },
            )

        result = self.client.session["monitor_state_impact"]
        self.assertRedirects(
            response,
            "/monitor/computadores/",
            fetch_redirect_response=False,
        )
        self.assertEqual(result["active_session"]["session_id"], session.pk)
        self.assertEqual(result["active_session"]["action"], "REALLOCATED")
        self.assertEqual(
            result["active_session"]["to_computer_id"], self.other_computer.pk
        )

        page = self.client.get("/monitor/computadores/")
        self.assertContains(page, "Sessão realocada")
        self.assertContains(page, "Falha no monitor")
        self.computer.refresh_from_db()
        self.assertEqual(
            self.computer.operational_state, Computer.OperationalState.MAINTENANCE
        )
        self.assertEqual(
            session.allocations.get(ended_at__isnull=True).computer,
            self.other_computer,
        )

    def test_monitor_can_create_and_follow_occurrence(self):
        self.select_monitor()

        created = self.client.post(
            "/monitor/ocorrencias/",
            {
                "computer_id": self.computer.pk,
                "description": "Teclado com tecla solta.",
            },
        )
        occurrence = Occurrence.objects.get()
        transitioned = self.client.post(
            f"/monitor/ocorrencias/{occurrence.pk}/transicao/",
            {"status": Occurrence.Status.IN_REVIEW},
        )

        self.assertRedirects(created, "/monitor/ocorrencias/")
        self.assertRedirects(transitioned, "/monitor/ocorrencias/")
        occurrence.refresh_from_db()
        self.assertEqual(occurrence.status, Occurrence.Status.IN_REVIEW)
        page = self.client.get("/monitor/ocorrencias/?q=teclado")
        self.assertContains(page, "Teclado com tecla solta")
        self.assertContains(page, "Em análise")

    def test_monitor_corrects_allowed_history_fields_with_reason(self):
        session = self.create_session(active=False)
        self.select_monitor()
        corrected_start = self.aware(time(8, 5))
        corrected_end = self.aware(time(8, 50))

        response = self.client.post(
            f"/monitor/historico/{session.pk}/corrigir/",
            {
                "started_at": corrected_start.isoformat(),
                "ended_at": corrected_end.isoformat(),
                "reason": "Conferência no registro físico de entrada e saída.",
            },
        )

        self.assertRedirects(response, f"/monitor/historico/{session.pk}/")
        session.refresh_from_db()
        allocation = session.allocations.get()
        self.assertEqual(session.started_at, corrected_start)
        self.assertEqual(session.ended_at, corrected_end)
        self.assertEqual(allocation.started_at, corrected_start)
        self.assertEqual(allocation.ended_at, corrected_end)
        self.assertTrue(
            AuditEvent.objects.filter(
                action="USAGE_SESSION_CORRECTED",
                entity_id=str(session.pk),
                reason__icontains="registro físico",
            ).exists()
        )

    def test_invalid_correction_is_rendered_without_mutating_history(self):
        session = self.create_session(active=False)
        original_start = session.started_at
        self.select_monitor()

        response = self.client.post(
            f"/monitor/historico/{session.pk}/corrigir/",
            {"started_at": self.aware(time(7, 30)).isoformat(), "reason": "Teste"},
        )

        self.assertEqual(response.status_code, 409)
        self.assertContains(response, 'role="alert"', status_code=409)
        session.refresh_from_db()
        self.assertEqual(session.started_at, original_start)
