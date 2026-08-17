from django.utils import timezone
from rest_framework.test import APITestCase

from apps.computers.models import Computer
from apps.occurrences.models import Occurrence
from apps.operations.models import ComputerAllocation
from apps.operations.tests.factories import create_use_session


class OccurrenceAPITest(APITestCase):
    def setUp(self):
        self.computer = Computer.objects.create(code="PC-01")
        self.other_computer = Computer.objects.create(code="PC-02")
        self.session = create_use_session(
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
            "/api/demo/select-profile/",
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
            "/api/demo/select-profile/",
            {"profile": "ROOM_MONITOR"},
            format="json",
        )

    def test_room_user_creates_occurrence_linked_to_current_allocation(self):
        response = self.client.post(
            "/api/occurrences/",
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
            "/api/occurrences/",
            {"description": "Problema observado antes da entrada."},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertIsNone(Occurrence.objects.get().session)

    def test_creation_rejects_empty_description_and_missing_computer(self):
        empty_response = self.client.post(
            "/api/occurrences/",
            {"description": "   "},
            format="json",
        )
        missing_response = self.client.post(
            "/api/occurrences/",
            {"computer_id": 9999, "description": "Computador inexistente."},
            format="json",
        )

        self.assertEqual(empty_response.status_code, 400)
        self.assertEqual(missing_response.status_code, 404)

    def test_creation_rejects_allocation_from_another_session(self):
        other_session = create_use_session(
            user_reference="aluno-si-002",
            entry_recorded_by_profile="ROOM_USER",
        )

        response = self.client.post(
            "/api/occurrences/",
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

        list_response = self.client.get("/api/occurrences/")
        hidden_detail = self.client.get(f"/api/occurrences/{other.pk}/")
        self.select_operational_profile()
        operational_list = self.client.get("/api/occurrences/")

        self.assertEqual(
            [item["id"] for item in list_response.data["results"]], [own.pk]
        )
        self.assertEqual(hidden_detail.status_code, 404)
        self.assertCountEqual(
            [item["id"] for item in operational_list.data["results"]],
            [own.pk, other.pk],
        )

    def test_occurrences_are_paginated_and_keep_profile_visibility(self):
        own = [
            Occurrence.objects.create(
                reported_by_reference="aluno-si-001",
                description=f"Ocorrência própria {index}",
            )
            for index in range(26)
        ]
        Occurrence.objects.create(
            reported_by_reference="aluno-si-002",
            description="Ocorrência de outra pessoa",
        )

        first_page = self.client.get("/api/occurrences/")
        second_page = self.client.get("/api/occurrences/?page=2")

        self.assertEqual(first_page.data["count"], 26)
        self.assertEqual(len(first_page.data["results"]), 25)
        self.assertEqual(first_page.data["results"][0]["id"], own[-1].pk)
        self.assertEqual(len(second_page.data["results"]), 1)
        self.assertNotContains(second_page, "Ocorrência de outra pessoa")

    def test_operational_profile_moves_occurrence_to_review_and_resolves_it(self):
        occurrence = Occurrence.objects.create(
            reported_by_reference="aluno-si-001",
            description="Monitor com falha.",
        )
        self.select_operational_profile()

        review_response = self.client.patch(
            f"/api/occurrences/{occurrence.pk}/",
            {"status": "IN_REVIEW"},
            format="json",
        )
        resolved_response = self.client.patch(
            f"/api/occurrences/{occurrence.pk}/",
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
        self.assertEqual(occurrence.resolved_by_profile, "ROOM_MONITOR")
        self.assertEqual(occurrence.resolution_notes, "Cabo reconectado.")
        self.assertLessEqual(occurrence.resolved_at, timezone.now())

    def test_resolution_requires_notes_and_rejects_invalid_transition(self):
        occurrence = Occurrence.objects.create(
            reported_by_reference="aluno-si-001",
            description="Monitor com falha.",
        )
        self.select_operational_profile()

        direct_resolution = self.client.patch(
            f"/api/occurrences/{occurrence.pk}/",
            {"status": "RESOLVED", "resolution_notes": "Resolvido."},
            format="json",
        )
        self.client.patch(
            f"/api/occurrences/{occurrence.pk}/",
            {"status": "IN_REVIEW"},
            format="json",
        )
        missing_notes = self.client.patch(
            f"/api/occurrences/{occurrence.pk}/",
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
            f"/api/occurrences/{occurrence.pk}/",
            {"status": "IN_REVIEW"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
