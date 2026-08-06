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

    def test_home_loads_public_room_notices_before_profile_selection(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="room-notices"')
        self.assertContains(response, "/api/room-notices/active/")
