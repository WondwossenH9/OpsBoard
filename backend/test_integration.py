import unittest

import mysql.connector
from app import DB_CONFIG, app


class IncidentIntegrationTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.connection = mysql.connector.connect(**DB_CONFIG)

        with cls.connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS incidents (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    severity VARCHAR(50) NOT NULL
                )
                """
            )

            cursor.execute("TRUNCATE TABLE incidents")

            cursor.executemany(
                """
                INSERT INTO incidents (title, status, severity)
                VALUES (%s, %s, %s)
                """,
                [
                    ("Database outage", "open", "critical"),
                    ("API latency", "investigating", "high"),
                ],
            )

        cls.connection.commit()
        cls.client = app.test_client()

    @classmethod
    def tearDownClass(cls):
        with cls.connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE incidents")

        cls.connection.commit()
        cls.connection.close()

    def test_get_incidents_from_real_mysql(self):
        response = self.client.get("/api/incidents")
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["total"], 2)

        self.assertEqual(
            data["incidents"],
            [
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
            ],
        )

    def test_get_existing_incident_from_real_mysql(self):
        response = self.client.get("/api/incidents/1")
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            data,
            {
                "id": 1,
                "title": "Database outage",
                "status": "open",
                "severity": "critical",
            },
        )

    def test_get_missing_incident_returns_404(self):
        response = self.client.get("/api/incidents/999")
        data = response.get_json()

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            data,
            {
                "error": "Not Found",
                "message": "Incident with ID 999 was not found.",
            },
        )


if __name__ == "__main__":
    unittest.main()
