# OpsBoard

OpsBoard is a production-inspired incident management platform built to demonstrate modern DevOps and cloud engineering practices.

The project is being developed incrementally using real-world engineering workflows, progressing from a simple Flask REST API into a containerized multi-service platform with persistent data, reverse proxying, automated testing, CI/CD, versioned release artifacts, database migrations, and reproducible deployment environments.

The goal is not simply to build an application.

The goal is to understand and demonstrate how an application is:

- developed;
- tested;
- containerized;
- networked;
- configured;
- persisted;
- released;
- operated;
- diagnosed when it fails;
- and progressively prepared for cloud and production environments.

---

## Current Status

**Sprint 7 — CI/CD & Release Engineering**

OpsBoard now supports an automated delivery flow from feature branch to a versioned container artifact.

The current platform includes:

- **Nginx** — public reverse proxy
- **Gunicorn** — production WSGI server
- **Flask** — backend REST API
- **MySQL 8.0** — persistent database
- **Docker Compose** — local multi-service orchestration
- **GitHub Actions** — CI and release automation
- **GitHub Container Registry (GHCR)** — backend container registry
- **SQL migration job** — reproducible database schema bootstrap
- **Protected `main` branch** — enforced CI before merge

The project currently demonstrates both:

```text
Development workflow
```

and:

```text
Release workflow
```

The next major phase is AWS deployment.

---

## Current Architecture

```text
                         Client
                           |
                           | HTTP :80
                           v
                  +------------------+
                  |      Nginx       |
                  |  Reverse Proxy   |
                  +---------+--------+
                            |
                            | backend:8000
                            v
                  +------------------+
                  |     Gunicorn     |
                  |   WSGI Server    |
                  +---------+--------+
                            |
                            v
                  +------------------+
                  |      Flask       |
                  |     REST API     |
                  +---------+--------+
                            |
                            | mysql:3306
                            v
                  +------------------+
                  |      MySQL       |
                  |     Database     |
                  +---------+--------+
                            |
                            v
                  +------------------+
                  |   mysql_data     |
                  |  Named Volume    |
                  +------------------+
```

Database initialization in the release environment adds an additional startup stage:

```text
MySQL healthy
     ↓
migration job
     ↓
migration exits successfully
     ↓
Gunicorn backend starts
     ↓
Nginx starts
```

---

## CI/CD Architecture

Changes are developed through feature branches and pull requests.

```text
Developer
    ↓
Feature Branch
    ↓
Pull Request
    ↓
┌─────────────────────┐
│ backend-ci          │
│ integration-tests   │
└─────────────────────┘
    ↓
Required checks pass
    ↓
Protected main
```

Pull requests run CI but do not publish release artifacts.

After a successful merge:

```text
Push to main
    ↓
backend-ci
    +
integration-tests
    ↓
both succeed
    ↓
publish-image
    ↓
GitHub Container Registry
```

The backend image is published as:

```text
ghcr.io/wondwossenh9/opsboard-backend:<git-commit-sha>
```

and:

```text
ghcr.io/wondwossenh9/opsboard-backend:latest
```

The commit-SHA tag provides traceability between source code and the released container artifact.

---

## CI Jobs

### `backend-ci`

Validates the backend application without requiring a real external database.

The job performs:

```text
Checkout repository
        ↓
Set up Python 3.12
        ↓
Install dependencies
        ↓
Validate Python syntax
        ↓
Run unit tests
        ↓
Build Docker image
```

Syntax validation uses:

```bash
python -m compileall backend
```

Unit tests use Python's built-in:

```text
unittest
```

framework.

---

### `integration-tests`

Runs the Flask application against a real MySQL 8.0 service container.

The GitHub Actions runner communicates with the service through:

```text
127.0.0.1:3306
```

The integration tests create controlled database state, seed known test records, execute API requests, and clean up afterward.

---

### `publish-image`

The release job runs only when:

```text
event = push
branch = main
```

and only after:

```text
backend-ci
integration-tests
```

both succeed.

Package publication therefore occurs only from validated code on `main`.

The job uses:

```text
contents: read
packages: write
```

permissions and authenticates to GHCR using GitHub's workflow-provided token rather than a hardcoded registry credential.

---

## Automated Test Coverage

OpsBoard currently contains:

```text
5 unit tests
3 integration tests
```

### Unit Tests

The unit suite verifies:

- Health endpoint returns `200 OK`.
- Health endpoint returns the expected JSON contract.
- Incident collection returns mocked database rows correctly.
- Incident collection returns `503 Service Unavailable` when the database fails.
- Single-incident endpoint returns `503 Service Unavailable` when the database fails.

Mocks are used where the goal is to test application behavior independently of infrastructure.

### Integration Tests

The integration suite uses real MySQL and verifies:

- Incident collection retrieval.
- Existing incident retrieval.
- Missing incident returns `404 Not Found`.

This provides two complementary testing layers:

```text
Unit tests
→ application behavior in isolation

Integration tests
→ Flask + mysql.connector + real MySQL
```

---

## Branch Protection

The `main` branch is protected.

The following checks must pass before a pull request can be merged:

```text
backend-ci
integration-tests
```

This means CI is not merely advisory.

A failed required check prevents the change from entering `main`.

The release job is intentionally not required on pull requests because publishing only occurs after merge.

---

## Application Endpoints

### Root

```text
GET /
```

Returns API metadata and available endpoints.

Example:

```json
{
  "health": "/api/health",
  "incidents": "/api/incidents",
  "message": "Welcome to OpsBoard API",
  "status": "running",
  "version": "1.0.0"
}
```

### Health

```text
GET /api/health
```

Example:

```json
{
  "environment": "development",
  "service": "OpsBoard API",
  "status": "healthy",
  "version": "1.0.0"
}
```

### List Incidents

```text
GET /api/incidents
```

Example:

```json
{
  "incidents": [
    {
      "id": 1,
      "severity": "high",
      "status": "investigating",
      "title": "Database Connection Timeout"
    }
  ],
  "total": 1
}
```

### Retrieve Incident

```text
GET /api/incidents/<id>
```

A nonexistent incident returns:

```text
404 Not Found
```

### Database Failure

When MySQL is unavailable, database-backed endpoints return:

```text
503 Service Unavailable
```

with a safe client-facing response:

```json
{
  "error": "Service Unavailable",
  "message": "The database is currently unavailable."
}
```

Detailed database errors remain in server-side logs.

---

## Production Runtime

The backend container is served using:

```text
Gunicorn 26.2.0
```

rather than Flask's development server.

The container starts with two Gunicorn workers and listens on:

```text
0.0.0.0:8000
```

The runtime request path is:

```text
Nginx
  ↓
Gunicorn
  ↓
Flask
  ↓
MySQL
```

Gunicorn access and error logs are written to container stdout/stderr so they remain available through Docker logging.

---

## Development vs. Release Configuration

OpsBoard deliberately separates local development from release execution.

### Development

`compose.yaml` builds the backend from local source:

```yaml
backend:
  build:
    context: ./backend
```

This supports fast local iteration.

### Release

`compose.release.yaml` consumes a previously published backend image:

```yaml
backend:
  image: ${BACKEND_IMAGE:?BACKEND_IMAGE must be set}
```

This means release environments run a tested artifact rather than rebuilding the backend from whatever source happens to exist on the deployment machine.

The principle is:

```text
Build once
    ↓
publish artifact
    ↓
configure at runtime
    ↓
deploy the same artifact
```

---

## Database Migration

The release environment includes a version-controlled migration:

```text
db/migrations/001_create_incidents.sql
```

It creates the initial `incidents` schema.

A one-shot Compose service applies the migration before the backend starts.

```text
MySQL
  ↓ service_healthy
migrate
  ↓ service_completed_successfully
backend
  ↓
Nginx
```

A successful migration container is expected to exit with:

```text
Exited (0)
```

If migration fails, backend startup is blocked.

This prevents the application from starting against a database whose schema preparation failed.

---

## MySQL Readiness

The release MySQL health check verifies TCP readiness using:

```text
mysqladmin ping
--protocol=TCP
-h 127.0.0.1
```

This was chosen because downstream containers communicate with MySQL through TCP.

The distinction is important:

```text
container started
        ≠
database ready for clients
```

and:

```text
local socket works
        ≠
TCP dependency is ready
```

---

## Persistent Storage

MySQL data is stored in a Docker named volume.

Development uses:

```text
opsboard_mysql_data
```

The isolated release project uses its own release-scoped volume.

Persistent storage is therefore separated from container lifecycle.

```bash
docker compose down
```

removes containers while preserving the volume.

```bash
docker compose down -v
```

also deletes the database volume.

---

## Configuration and Secret Hygiene

Application configuration is supplied through environment variables.

The backend receives:

```text
DB_HOST
DB_PORT
DB_NAME
DB_USER
DB_PASSWORD
```

MySQL initialization uses environment configuration as well.

The real:

```text
.env
```

file is excluded from version control.

The repository contains:

```text
.env.example
```

as a safe configuration template.

Example:

```env
MYSQL_ROOT_PASSWORD=change-me
MYSQL_DATABASE=mydatabase
MYSQL_USER=change-me
MYSQL_PASSWORD=change-me

DB_HOST=mysql
DB_PORT=3306
DB_NAME=mydatabase
DB_USER=change-me
DB_PASSWORD=change-me
```

No production or personal credentials should be committed to the repository.

---

## Running the Development Stack

Clone the repository and enter the project directory.

Create an environment file:

```bash
cp .env.example .env
```

Update the placeholder values.

Start the stack:

```bash
docker compose up -d --build
```

Check status:

```bash
docker compose ps
```

The API is available through Nginx at:

```text
http://localhost
```

---

## Running the Release Stack

The release stack requires a published backend image.

Example:

```bash
export BACKEND_IMAGE=ghcr.io/wondwossenh9/opsboard-backend:<git-commit-sha>
```

Then run the release environment under its own Compose project:

```bash
docker compose \
  -p opsboard-release \
  -f compose.release.yaml \
  up -d
```

Inspect all services, including the completed migration job:

```bash
docker compose \
  -p opsboard-release \
  -f compose.release.yaml \
  ps -a
```

A healthy startup should resemble:

```text
mysql      → Up (healthy)
migrate    → Exited (0)
backend    → Up
nginx      → Up
```

Test:

```bash
curl http://localhost/api/health
curl http://localhost/api/incidents
```

To remove the isolated release environment and its disposable database volume:

```bash
docker compose \
  -p opsboard-release \
  -f compose.release.yaml \
  down -v
```

---

## Repository Structure

```text
opsboard/
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── backend/
│   ├── app.py
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── test_app.py
│   ├── test_integration.py
│   └── .dockerignore
│
├── db/
│   └── migrations/
│       └── 001_create_incidents.sql
│
├── nginx/
│   ├── Dockerfile
│   └── nginx.conf
│
├── frontend/
│
├── docs/
│   └── engineering-journal.md
│
├── .env.example
├── .gitignore
├── compose.yaml
├── compose.release.yaml
├── CHANGELOG.md
└── README.md
```

---

## Technology Stack

### Application

- Python 3.12
- Flask 3.1.1
- Gunicorn 26.2.0
- MySQL Connector/Python 9.4.0

### Containers and Networking

- Docker
- Docker Compose
- Python 3.12 Slim
- MySQL 8.0
- Nginx Alpine
- Docker internal DNS
- Docker named volumes
- Container health checks

### CI/CD

- GitHub Actions
- Pull-request CI
- Required status checks
- Protected `main`
- Unit testing
- MySQL integration testing
- Docker build validation
- GitHub Container Registry
- SHA-tagged container releases

### Release Engineering

- Runtime configuration
- Version-controlled SQL migrations
- Dependency-aware startup
- Isolated release environments
- Immutable-artifact workflow
- Production WSGI serving
- Failure-path verification

---

## Engineering Approach

OpsBoard is intentionally developed using the following cycle:

```text
Understand
    ↓
Predict
    ↓
Build
    ↓
Break
    ↓
Diagnose
    ↓
Fix
    ↓
Verify
    ↓
Document
    ↓
Commit
    ↓
Release
    ↓
Share
```

Failures are deliberately investigated rather than hidden because operational troubleshooting is part of the project objective.

The engineering journal documents those failures, decisions, and lessons in detail.

---

## Roadmap

### Completed

- Flask API foundation
- Docker containerization
- Docker Compose networking
- Nginx reverse proxy
- MySQL persistence
- Environment-based configuration
- Database failure handling
- Unit testing
- MySQL integration testing
- GitHub Actions CI
- Protected `main`
- GHCR container publishing
- SHA-tagged release artifacts
- Release Compose environment
- Version-controlled database migration
- Gunicorn production runtime

### Next

```text
AWS Deployment
      ↓
Terraform Infrastructure as Code
      ↓
Kubernetes
      ↓
Observability
      ↓
Final production hardening
```

The next major milestone is deploying the existing release architecture to AWS while preserving the delivery principles already established locally.