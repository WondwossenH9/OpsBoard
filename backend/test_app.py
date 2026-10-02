import unittest

from app import app


class HealthCheckTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_health_check_returns_200(self):
        response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
