from rest_framework.test import APITestCase


class HealthAPITest(APITestCase):
    def test_health_endpoint(self):
        response = self.client.get("/api/v1/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ok")
        self.assertEqual(response.data["version"], "v1")

    def test_home_loads_public_room_notices_before_profile_selection(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="room-notices"')
        self.assertContains(response, "/api/v1/room-notices/active/")
