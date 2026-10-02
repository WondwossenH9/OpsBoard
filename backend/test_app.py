import unittest
from unittest.mock import MagicMock, patch

import mysql.connector
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


class IncidentTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    @patch("app.get_db_connection")
    def test_get_incidents_returns_database_rows(self, mock_get_db_connection):
        expected_incidents = [
            {
                "id": 1,
                "title": "Database outage",
                "status": "open",
                "severity": "critical",
            },
            {
                "id": 2,
                "title": "API latency",
                "status": "investigating",
                "severity": "high",
            },
        ]

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = expected_incidents

        mock_connection = MagicMock()
        mock_connection.__enter__.return_value = mock_connection
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

        mock_get_db_connection.return_value = mock_connection

        response = self.client.get("/api/incidents")
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["incidents"], expected_incidents)

    @patch("app.get_db_connection")
    def test_get_incidents_returns_503_when_database_unavailable(
        self, mock_get_db_connection
    ):
        mock_get_db_connection.side_effect = mysql.connector.Error(
            "Database unavailable"
        )

        response = self.client.get("/api/incidents")
        data = response.get_json()

        self.assertEqual(response.status_code, 503)
        self.assertEqual(data["error"], "Service Unavailable")
        self.assertEqual(
            data["message"],
            "The database is currently unavailable.",
        )


if __name__ == "__main__":
    unittest.main()
