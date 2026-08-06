from flask import Flask, jsonify, abort

app = Flask(__name__)

# Mock database (in-memory list of dictionaries)
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


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint to verify service availability."""
    return jsonify({"status": "healthy", "service": "incident-tracker"}), 200


@app.route("/api/incidents", methods=["GET"])
def get_incidents():
    """Retrieve all incidents."""
    return jsonify({"total": len(INCIDENTS), "incidents": INCIDENTS}), 200


@app.route("/api/incidents/<int:incident_id>", methods=["GET"])
def get_incident(incident_id):
    """Retrieve a single incident by its integer ID."""
    incident = next((item for item in INCIDENTS if item["id"] == incident_id), None)

    if incident is None:
        return jsonify(
            {
                "error": "Not Found",
                "message": f"Incident with ID {incident_id} was not found.",
            }
        ), 404

    return jsonify(incident), 200


if __name__ == "__main__":
    app.run(debug=True, port=8000)
