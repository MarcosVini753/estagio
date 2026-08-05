from django.utils import timezone
from rest_framework.test import APITestCase

from apps.computers.models import Computer
from apps.occurrences.models import Occurrence
from apps.operations.models import ComputerAllocation, UseSession


class OccurrenceAPITest(APITestCase):
    def setUp(self):
        self.computer = Computer.objects.create(code="PC-01")
        self.other_computer = Computer.objects.create(code="PC-02")
        self.session = UseSession.objects.create(
            user_reference="aluno-si-001",
            affiliation_type="STUDENT",
            institutional_unit="Sistemas de Informação",
            entry_recorded_by_profile="ROOM_USER",
        )
        self.allocation = ComputerAllocation.objects.create(
            session=self.session,
            computer=self.computer,
            sequence=1,
        )
        self.select_room_user()

    def select_room_user(self, reference="aluno-si-001"):
        self.client.post(
            "/api/v1/demo/select-profile/",
            {
                "profile": "ROOM_USER",
                "user_reference": reference,
                "affiliation_type": "STUDENT",
                "institutional_unit": "Sistemas de Informação",
            },
            format="json",
        )

    def select_operational_profile(self):
        self.client.post(
            "/api/v1/demo/select-profile/",
            {"profile": "INTERN"},
            format="json",
        )

    def test_room_user_creates_occurrence_linked_to_current_allocation(self):
        response = self.client.post(
            "/api/v1/occurrences/",
            {
                "computer_id": self.computer.pk,
                "session_id": self.session.pk,
                "allocation_id": self.allocation.pk,
                "description": "Teclado sem resposta.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        occurrence = Occurrence.objects.get()
        self.assertEqual(occurrence.reported_by_reference, "aluno-si-001")
        self.assertEqual(occurrence.session, self.session)
        self.assertEqual(occurrence.allocation, self.allocation)
        self.assertEqual(
            self.computer.operational_state,
            Computer.OperationalState.AVAILABLE,
        )

    def test_creation_without_session_is_allowed(self):
        response = self.client.post(
            "/api/v1/occurrences/",
            {"description": "Problema observado antes da entrada."},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertIsNone(Occurrence.objects.get().session)

    def test_creation_rejects_empty_description_and_missing_computer(self):
        empty_response = self.client.post(
            "/api/v1/occurrences/",
            {"description": "   "},
            format="json",
        )
        missing_response = self.client.post(
            "/api/v1/occurrences/",
            {"computer_id": 9999, "description": "Computador inexistente."},
            format="json",
        )

        self.assertEqual(empty_response.status_code, 400)
        self.assertEqual(missing_response.status_code, 404)

    def test_creation_rejects_allocation_from_another_session(self):
        other_session = UseSession.objects.create(
            user_reference="aluno-si-002",
            entry_recorded_by_profile="ROOM_USER",
        )

        response = self.client.post(
            "/api/v1/occurrences/",
            {
                "session_id": other_session.pk,
                "allocation_id": self.allocation.pk,
                "description": "Vínculo inválido.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "OCCURRENCE_LINK_INVALID")

    def test_room_user_only_sees_own_occurrences(self):
        own = Occurrence.objects.create(
            reported_by_reference="aluno-si-001",
            description="Própria",
        )
        other = Occurrence.objects.create(
            reported_by_reference="aluno-si-002",
            description="Outra",
        )

        list_response = self.client.get("/api/v1/occurrences/")
        hidden_detail = self.client.get(f"/api/v1/occurrences/{other.pk}/")
        self.select_operational_profile()
        operational_list = self.client.get("/api/v1/occurrences/")

        self.assertEqual([item["id"] for item in list_response.data], [own.pk])
        self.assertEqual(hidden_detail.status_code, 404)
        self.assertCountEqual(
            [item["id"] for item in operational_list.data],
            [own.pk, other.pk],
        )

    def test_operational_profile_moves_occurrence_to_review_and_resolves_it(self):
        occurrence = Occurrence.objects.create(
            reported_by_reference="aluno-si-001",
            description="Monitor com falha.",
        )
        self.select_operational_profile()

        review_response = self.client.patch(
            f"/api/v1/occurrences/{occurrence.pk}/",
            {"status": "IN_REVIEW"},
            format="json",
        )
        resolved_response = self.client.patch(
            f"/api/v1/occurrences/{occurrence.pk}/",
            {
                "status": "RESOLVED",
                "resolution_notes": "Cabo reconectado.",
            },
            format="json",
        )

        self.assertEqual(review_response.status_code, 200)
        self.assertEqual(resolved_response.status_code, 200)
        occurrence.refresh_from_db()
        self.assertEqual(occurrence.status, Occurrence.Status.RESOLVED)
        self.assertEqual(occurrence.resolved_by_profile, "INTERN")
        self.assertEqual(occurrence.resolution_notes, "Cabo reconectado.")
        self.assertLessEqual(occurrence.resolved_at, timezone.now())

    def test_resolution_requires_notes_and_rejects_invalid_transition(self):
        occurrence = Occurrence.objects.create(
            reported_by_reference="aluno-si-001",
            description="Monitor com falha.",
        )
        self.select_operational_profile()

        direct_resolution = self.client.patch(
            f"/api/v1/occurrences/{occurrence.pk}/",
            {"status": "RESOLVED", "resolution_notes": "Resolvido."},
            format="json",
        )
        self.client.patch(
            f"/api/v1/occurrences/{occurrence.pk}/",
            {"status": "IN_REVIEW"},
            format="json",
        )
        missing_notes = self.client.patch(
            f"/api/v1/occurrences/{occurrence.pk}/",
            {"status": "RESOLVED"},
            format="json",
        )

        self.assertEqual(direct_resolution.status_code, 409)
        self.assertEqual(missing_notes.status_code, 400)

    def test_room_user_cannot_update_occurrence(self):
        occurrence = Occurrence.objects.create(
            reported_by_reference="aluno-si-001",
            description="Monitor com falha.",
        )

        response = self.client.patch(
            f"/api/v1/occurrences/{occurrence.pk}/",
            {"status": "IN_REVIEW"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
