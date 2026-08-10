from flask import Flask, jsonify

app = Flask(__name__)

# -------------------------------------------------------------------
# Application Configuration
# -------------------------------------------------------------------

APP_NAME = "OpsBoard API"
APP_VERSION = "1.0.0"
APP_ENV = "development"

# -------------------------------------------------------------------
# Temporary in-memory data
# This will be replaced with MySQL in Sprint 3.
# -------------------------------------------------------------------

INCIDENTS = [
    {
        "id": 1,
        "title": "Database Connection Timeout",
        "status": "investigating",
        "severity": "high",
    },
    {
        "id": 2,
        "title": "High Memory Usage on API Gateway",
        "status": "resolved",
        "severity": "medium",
    },
    {
        "id": 3,
        "title": "SSL Certificate Expiration Warning",
        "status": "open",
        "severity": "low",
    },
]


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
    """Return all incidents."""

    return (
        jsonify(
            {
                "total": len(INCIDENTS),
                "incidents": INCIDENTS,
            }
        ),
        200,
    )


@app.route("/api/incidents/<int:incident_id>", methods=["GET"])
def get_incident(incident_id):
    """Return a single incident."""

    incident = next(
        (item for item in INCIDENTS if item["id"] == incident_id),
        None,
    )

    if incident is None:
        return (
            jsonify(
                {
                    "error": "Not Found",
                    "message": f"Incident with ID {incident_id} was not found.",
                }
            ),
            404,
        )

    return jsonify(incident), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
