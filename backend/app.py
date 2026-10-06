import os

import mysql.connector
from flask import Flask, jsonify

app = Flask(__name__)

# -------------------------------------------------------------------
# Application Configuration
# -------------------------------------------------------------------
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}


def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


APP_NAME = "OpsBoard API"
APP_VERSION = "1.0.0"
APP_ENV = "development"


# -------------------------------------------------------------------
# Error Handlers
# -------------------------------------------------------------------
@app.errorhandler(mysql.connector.Error)
def handle_database_error(error):
    app.logger.error("Database error: %s", error)

    return jsonify(
        {
            "error": "Service Unavailable",
            "message": "The database is currently unavailable.",
        }
    ), 503


# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------


@app.route("/")
def home():
    return jsonify(
        {
            "message": "Welcome to OpsBoard API",
            "status": "running",
            "version": APP_VERSION,
            "health": "/api/health",
            "incidents": "/api/incidents",
        }
    ), 200


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""

    return (
        jsonify(
            {
                "status": "healthy",
                "service": APP_NAME,
                "version": APP_VERSION,
                "environment": APP_ENV,
            }
        ),
        200,
    )


@app.route("/api/incidents", methods=["GET"])
def get_incidents():
    """Retrieve all incidents from MySQL."""

    with get_db_connection() as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                "SELECT id, title, status, severity FROM incidents ORDER BY id"
            )

            incidents = cursor.fetchall()

    return jsonify(
        {
            "total": len(incidents),
            "incidents": incidents,
        }
    ), 200


@app.route("/api/incidents/<int:incident_id>", methods=["GET"])
def get_incident(incident_id):
    """Retrieve a single incident from MySQL."""
    with get_db_connection() as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                """
                SELECT id, title, status, severity
                FROM incidents
                WHERE id = %s
                """,
                (incident_id,),
            )

            incident = cursor.fetchone()

    if incident is None:
        return jsonify(
            {
                "error": "Not Found",
                "message": f"Incident with ID {incident_id} was not found.",
            }
        ), 404

    return jsonify(incident), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
