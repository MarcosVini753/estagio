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

    def test_rejects_unknown_profile(self):
        response = self.client.post(
            "/api/v1/demo/select-profile/",
            {"profile": "UNKNOWN"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "VALIDATION_ERROR")
        self.assertIn("profile", response.data["fields"])
