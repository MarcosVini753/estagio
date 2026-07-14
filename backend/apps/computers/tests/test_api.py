from rest_framework.test import APITestCase

from apps.computers.models import Computer, ComputerOperationalStateChange


class ComputerAPITest(APITestCase):
    def select_profile(self, profile):
        self.client.post(
            "/api/v1/demo/select-profile/",
            {"profile": profile},
            format="json",
        )

    def test_requires_selected_demo_profile(self):
        response = self.client.get("/api/v1/computers/")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "PERMISSION_DENIED")

    def test_room_user_can_list_but_cannot_create_computer(self):
        Computer.objects.create(code="PC-01")
        self.select_profile("ROOM_USER")

        list_response = self.client.get("/api/v1/computers/")
        create_response = self.client.post(
            "/api/v1/computers/",
            {"code": "PC-02"},
            format="json",
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(create_response.status_code, 403)

    def test_supervisor_can_create_computer(self):
        self.select_profile("LIBRARY_SUPERVISOR")

        response = self.client.post(
            "/api/v1/computers/",
            {
                "code": "PC-01",
                "description": "Computador de demonstração",
                "operational_state": "AVAILABLE",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["code"], "PC-01")
        self.assertEqual(Computer.objects.count(), 1)

    def test_intern_changes_operational_state_and_creates_history(self):
        computer = Computer.objects.create(code="PC-01")
        self.select_profile("INTERN")

        response = self.client.patch(
            f"/api/v1/computers/{computer.pk}/operational-state/",
            {
                "operational_state": "MAINTENANCE",
                "reason": "Monitor sem imagem",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        computer.refresh_from_db()
        self.assertEqual(computer.operational_state, "MAINTENANCE")
        change = ComputerOperationalStateChange.objects.get(computer=computer)
        self.assertEqual(change.actor_profile, "INTERN")
        self.assertEqual(change.reason, "Monitor sem imagem")

    def test_reason_is_required_to_make_computer_unavailable(self):
        computer = Computer.objects.create(code="PC-01")
        self.select_profile("INTERN")

        response = self.client.patch(
            f"/api/v1/computers/{computer.pk}/operational-state/",
            {"operational_state": "INACTIVE"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "STATE_CHANGE_REASON_REQUIRED")
        computer.refresh_from_db()
        self.assertEqual(computer.operational_state, "AVAILABLE")
