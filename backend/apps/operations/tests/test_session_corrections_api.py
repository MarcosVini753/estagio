from datetime import datetime, time
from unittest.mock import patch

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.audit.models import AuditEvent
from apps.computers.models import Computer
from apps.operations.models import ComputerAllocation, UseSession

from .factories import create_use_session


class SessionCorrectionAPITest(APITestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.computer = Computer.objects.create(code="PC-01")
        self.session = create_use_session(
            user_reference="aluno-si-001",
            started_at=self.aware(time(8, 0)),
            planned_ends_at=self.aware(time(10)),
            exit_deadline_at=self.aware(time(10, 3)),
            entry_recorded_by_profile="ROOM_USER",
        )
        self.allocation = ComputerAllocation.objects.create(
            session=self.session,
            computer=self.computer,
            sequence=1,
            started_at=self.aware(time(8, 0)),
        )
        self.client.post(
            "/api/demo/select-profile/",
            {"profile": "INTERN"},
            format="json",
        )

    def aware(self, value):
        return timezone.make_aware(
            datetime.combine(self.today, value),
            timezone.get_current_timezone(),
        )

    def correct(self, payload):
        return self.client.post(
            f"/api/usage-sessions/{self.session.pk}/correct/",
            payload,
            format="json",
        )

    def test_records_forgotten_exit_and_audit_event(self):
        response = self.correct(
            {
                "ended_at": self.aware(time(10, 0)).isoformat(),
                "reason": "Usuário esqueceu de registrar a saída.",
            }
        )

        self.assertEqual(response.status_code, 200)
        self.session.refresh_from_db()
        self.allocation.refresh_from_db()
        self.assertEqual(self.session.status, UseSession.Status.FINISHED)
        self.assertEqual(self.session.ended_at, self.aware(time(10, 0)))
        self.assertEqual(self.allocation.ended_at, self.aware(time(10, 0)))
        self.assertEqual(
            self.allocation.end_reason,
            ComputerAllocation.EndReason.ADMIN_CORRECTION,
        )
        event = AuditEvent.objects.get(action="USAGE_SESSION_CORRECTED")
        self.assertEqual(event.entity_id, str(self.session.pk))
        self.assertEqual(event.old_values["session"]["status"], "ACTIVE")
        self.assertEqual(event.new_values["session"]["status"], "FINISHED")

    def test_corrects_entry_and_synchronizes_first_allocation(self):
        response = self.correct(
            {
                "started_at": self.aware(time(8, 5)).isoformat(),
                "reason": "Horário de entrada digitado incorretamente.",
            }
        )

        self.assertEqual(response.status_code, 200)
        self.session.refresh_from_db()
        self.allocation.refresh_from_db()
        self.assertEqual(self.session.started_at, self.aware(time(8, 5)))
        self.assertEqual(self.allocation.started_at, self.aware(time(8, 5)))

    def test_corrects_last_interval_after_switch(self):
        self.allocation.ended_at = self.aware(time(9, 0))
        self.allocation.end_reason = ComputerAllocation.EndReason.SWITCH
        self.allocation.save(update_fields=["ended_at", "end_reason", "updated_at"])
        second_computer = Computer.objects.create(code="PC-02")
        last = ComputerAllocation.objects.create(
            session=self.session,
            computer=second_computer,
            sequence=2,
            started_at=self.aware(time(9, 0)),
        )

        response = self.correct(
            {
                "last_allocation_started_at": self.aware(time(9, 5)).isoformat(),
                "ended_at": self.aware(time(10, 0)).isoformat(),
                "reason": "Ajuste após conferência do registro.",
            }
        )

        self.assertEqual(response.status_code, 200)
        last.refresh_from_db()
        self.assertEqual(last.started_at, self.aware(time(9, 5)))
        self.assertEqual(last.ended_at, self.aware(time(10, 0)))

    def test_rejects_end_before_start_and_rolls_back(self):
        response = self.correct(
            {
                "ended_at": self.aware(time(7, 0)).isoformat(),
                "reason": "Valor inválido para teste.",
            }
        )

        self.assertEqual(response.status_code, 409)
        self.session.refresh_from_db()
        self.allocation.refresh_from_db()
        self.assertEqual(self.session.status, UseSession.Status.ACTIVE)
        self.assertIsNone(self.allocation.ended_at)
        self.assertFalse(AuditEvent.objects.exists())

    def test_rejects_conflicting_fields_and_missing_reason(self):
        conflicting = self.correct(
            {
                "started_at": self.aware(time(7, 30)).isoformat(),
                "last_allocation_started_at": self.aware(time(7, 45)).isoformat(),
                "reason": "Conflito proposital.",
            }
        )
        missing_reason = self.correct(
            {"started_at": self.aware(time(7, 45)).isoformat(), "reason": " "}
        )

        self.assertEqual(conflicting.status_code, 409)
        self.assertEqual(missing_reason.status_code, 400)

    def test_room_user_cannot_correct_session(self):
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

        response = self.correct(
            {
                "started_at": self.aware(time(7, 45)).isoformat(),
                "reason": "Tentativa sem permissão.",
            }
        )

        self.assertEqual(response.status_code, 403)

    def test_rejects_overlap_with_another_session(self):
        other_session = create_use_session(
            user_reference="aluno-si-002",
            started_at=self.aware(time(7, 0)),
            ended_at=self.aware(time(7, 45)),
            status=UseSession.Status.FINISHED,
            entry_recorded_by_profile="ROOM_USER",
        )
        ComputerAllocation.objects.create(
            session=other_session,
            computer=self.computer,
            sequence=1,
            started_at=self.aware(time(7, 0)),
            ended_at=self.aware(time(7, 45)),
        )

        response = self.correct(
            {
                "started_at": self.aware(time(7, 30)).isoformat(),
                "reason": "Criaria sobreposição.",
            }
        )

        self.assertEqual(response.status_code, 409)

    def test_rolls_back_when_audit_creation_fails(self):
        with (
            patch(
                "apps.operations.services.corrections.AuditEvent.objects.create",
                side_effect=RuntimeError("falha de auditoria"),
            ),
            self.assertRaises(RuntimeError),
        ):
            self.correct(
                {
                    "ended_at": self.aware(time(10, 0)).isoformat(),
                    "reason": "Correção com falha intermediária.",
                }
            )

        self.session.refresh_from_db()
        self.allocation.refresh_from_db()
        self.assertEqual(self.session.status, UseSession.Status.ACTIVE)
        self.assertIsNone(self.allocation.ended_at)
