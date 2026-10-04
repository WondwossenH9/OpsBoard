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


if __name__ == "__main__":
    unittest.main()
