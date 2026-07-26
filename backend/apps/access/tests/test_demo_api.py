from rest_framework.test import APITestCase


class DemoProfileAPITest(APITestCase):
    def test_context_starts_without_selected_profile(self):
        response = self.client.get("/api/v1/demo/context/")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["profile"])
        self.assertEqual(len(response.data["available_profiles"]), 4)

    def test_select_profile_persists_in_session(self):
        response = self.client.post(
            "/api/v1/demo/select-profile/",
            {"profile": "INTERN"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["profile"], "INTERN")
        self.assertEqual(self.client.session["demo_profile"], "INTERN")

    def test_room_user_requires_identity(self):
        response = self.client.post(
            "/api/v1/demo/select-profile/",
            {"profile": "ROOM_USER"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("user_reference", response.data["fields"])

    def test_room_user_identity_is_returned_in_context(self):
        response = self.client.post(
            "/api/v1/demo/select-profile/",
            {
                "profile": "ROOM_USER",
                "user_reference": "aluno-si-001",
                "affiliation_type": "STUDENT",
                "institutional_unit": "Sistemas de Informação",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user_reference"], "aluno-si-001")
        self.assertEqual(response.data["affiliation_type"], "STUDENT")
        context = self.client.get("/api/v1/demo/context/")
        self.assertEqual(context.data["institutional_unit"], "Sistemas de Informação")

    def test_operational_profile_clears_room_user_identity(self):
        self.client.post(
            "/api/v1/demo/select-profile/",
            {
                "profile": "ROOM_USER",
                "user_reference": "aluno-si-001",
                "affiliation_type": "STUDENT",
                "institutional_unit": "Sistemas de Informação",
            },
            format="json",
        )

        response = self.client.post(
            "/api/v1/demo/select-profile/",
            {"profile": "INTERN"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user_reference"], "demo-intern")
        self.assertIsNone(response.data["affiliation_type"])
        self.assertNotIn("demo_institutional_unit", self.client.session)

    def test_rejects_unknown_profile(self):
        response = self.client.post(
            "/api/v1/demo/select-profile/",
            {"profile": "UNKNOWN"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "VALIDATION_ERROR")
        self.assertIn("profile", response.data["fields"])
