import unittest

from app import app


class HealthCheckTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_health_check_returns_200(self):
        response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)

    def test_health_check_returns_expected_json(self):
        response = self.client.get("/api/health")
        data = response.get_json()

        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "OpsBoard API")
        self.assertEqual(data["version"], "1.0.0")
        self.assertEqual(data["environment"], "development")


if __name__ == "__main__":
    unittest.main()
