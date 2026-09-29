from django.test import TestCase

from apps.access.tests.helpers import login_test_account
from apps.computers.models import Computer
from apps.core.enums import DemoProfile
from apps.occurrences.models import Occurrence


class CrossProfileOccurrenceFlowTest(TestCase):
    def setUp(self):
        self.computer = Computer.objects.create(
            code="PC-01",
            description="Computador de teste interligado",
        )
        self.description = "Teclado com falha no fluxo entre perfis."
        self.resolution_notes = "Teclado substituído pela equipe da biblioteca."

    def login_room_user(self, reference):
        login_test_account(
            self.client,
            DemoProfile.ROOM_USER,
            user_reference=reference,
        )

    def login_operational_profile(self, profile, destination):
        login_test_account(self.client, profile)
        self.assertEqual(
            destination,
            {
                DemoProfile.ROOM_MONITOR: "/monitor/",
                DemoProfile.LIBRARY_SUPERVISOR: "/supervisor/",
            }[profile],
        )

    def test_occurrence_lifecycle_preserves_scope_and_returns_to_room_user(self):
        owner_reference = "aluno-fluxo-001"
        self.login_room_user(owner_reference)

        created = self.client.post(
            "/sala/problemas/",
            {
                "computer_id": self.computer.pk,
                "description": self.description,
            },
        )
        self.assertRedirects(created, "/sala/problemas/")
        occurrence = Occurrence.objects.get()
        self.assertEqual(occurrence.reported_by_reference, owner_reference)
        self.assertEqual(occurrence.status, Occurrence.Status.OPEN)

        self.login_room_user("aluno-fluxo-002")
        other_user_page = self.client.get("/sala/problemas/")
        self.assertNotContains(other_user_page, self.description)

        self.login_operational_profile(DemoProfile.ROOM_MONITOR, "/monitor/")
        monitoring_page = self.client.get("/monitor/ocorrencias/")
        self.assertContains(monitoring_page, self.description)
        in_review = self.client.post(
            f"/monitor/ocorrencias/{occurrence.pk}/transicao/",
            {"status": Occurrence.Status.IN_REVIEW},
        )
        self.assertRedirects(in_review, "/monitor/ocorrencias/")

        self.login_operational_profile(
            DemoProfile.LIBRARY_SUPERVISOR,
            "/supervisor/",
        )
        resolved = self.client.post(
            f"/monitor/ocorrencias/{occurrence.pk}/transicao/",
            {
                "status": Occurrence.Status.RESOLVED,
                "resolution_notes": self.resolution_notes,
            },
        )
        self.assertRedirects(resolved, "/monitor/ocorrencias/")

        occurrence.refresh_from_db()
        self.assertEqual(occurrence.status, Occurrence.Status.RESOLVED)
        self.assertEqual(
            occurrence.resolved_by_profile,
            DemoProfile.LIBRARY_SUPERVISOR,
        )
        self.assertEqual(occurrence.resolution_notes, self.resolution_notes)

        self.login_room_user(owner_reference)
        owner_page = self.client.get("/sala/problemas/")
        self.assertContains(owner_page, self.description)
        self.assertContains(owner_page, "Resolvida")
        self.assertContains(owner_page, self.resolution_notes)
