from rest_framework.test import APITestCase


class HealthAPITest(APITestCase):
    def test_health_endpoint(self):
        response = self.client.get("/api/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ok")
        self.assertNotIn("version", response.data)

    def test_versioned_api_path_is_not_available(self):
        response = self.client.get("/api/v1/health/")

        self.assertEqual(response.status_code, 404)

    def test_home_exposes_profile_selection_and_demo_warning(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="ROOM_USER"')
        self.assertContains(response, 'value="ROOM_MONITOR"')
        self.assertContains(response, "Autorização simulada")
