# OpsBoard Engineering Journal

## Sprint 2

### Learned

Docker layer caching depends on instruction order.

### Mistake

Forgot to save the Dockerfile before building.

### Lesson

Always verify the artifact exists before debugging Docker.

### Decision

Use `python:3.12-slim` as the base image to reduce image size and attack surface.

---

## Sprint 3 — Containerizing the Flask API

### Objective

Package the OpsBoard Flask API into a Docker image and run it as an isolated container.

### Work Completed

* Created a Dockerfile for the Flask API.
* Added a `.dockerignore` file.
* Used `python:3.12-slim` as the Docker base image.
* Installed Python dependencies inside the image.
* Built the Docker image as `opsboard-api:v1`.
* Ran the Flask API inside a Docker container.
* Used Docker port publishing to make the containerized API accessible from the host.

### Important Configuration Change

The Flask application initially listened on:

```text
127.0.0.1:8000
```

This worked for the Flask process itself but prevented access from outside the container.

The application was changed to listen on:

```text
0.0.0.0:8000
```

This allowed Docker's port forwarding to reach the Flask process.

The container was run with:

```text
-p 8000:8000
```

which mapped host port `8000` to container port `8000`.

### Docker Lifecycle

Used:

```text
--rm
```

for test containers so that the temporary container was automatically removed after it stopped.

This reinforced the distinction between:

* Docker images as reusable application artifacts.
* Containers as runtime instances of those images.

### Networking

The container received a Docker bridge-network IP and was reachable through Docker's host-to-container port mapping.

### Mistakes and Debugging

Two important issues were encountered:

1. The Flask application initially bound to `127.0.0.1`, preventing external access to the containerized service.
2. `.dockerignore` was initially forgotten and was subsequently added.

### Key Engineering Lessons

* A process listening on `localhost` inside a container is not automatically reachable from outside the container.
* Container networking and application binding must work together.
* Port publishing connects a host port to a container port; it does not change what address the application listens on.
* Containers are runtime instances; images are reusable artifacts.
* `.dockerignore` prevents unnecessary files from entering the Docker build context.

### Sprint 3 Outcome

OpsBoard's Flask API successfully ran as a Dockerized application and could be accessed through the host using Docker port forwarding.

---

## Sprint 4 — Reverse Proxy & Multi-Container Networking

### Objective

Introduce Nginx as the entry point for OpsBoard and establish communication between multiple containers using Docker Compose networking.

### Architecture

The architecture evolved from a single container to:

```text
Browser
   ↓
Nginx :80
   ↓
Flask :8000
```

Two services were introduced:

* `backend`
* `nginx`

Both services ran on the same Docker Compose network.

### Nginx Reverse Proxy

Nginx was configured to forward incoming HTTP requests to:

```text
http://backend:8000
```

The backend was therefore no longer directly exposed to the host.

Only Nginx published a host port:

```text
Host :80 → Nginx :80
```

The Flask backend remained reachable only inside the Compose network.

### Docker Compose Networking

Docker Compose automatically created a network for the services.

The backend could be reached using the Compose service name:

```text
backend
```

rather than relying on a hardcoded container IP address.

This introduced an important infrastructure principle:

> Services should communicate through stable service names rather than ephemeral container IP addresses.

### `depends_on`

We also clarified the role of:

```yaml
depends_on:
  - backend
```

`depends_on` establishes startup ordering, but it does not mean that the backend is necessarily ready to serve requests.

Nginx's `proxy_pass` configuration determines where requests are actually routed.

### Testing

The multi-container stack was successfully built and started with Docker Compose.

Requests through Nginx successfully reached the Flask backend.

The following behavior was verified:

* `/api/health` worked through Nginx.
* `/api/incidents` worked through Nginx.
* Direct communication from Nginx to `http://backend:8000` worked.
* `/` initially returned `404` because Flask did not yet have a root route.

The `404` was correctly identified as an application-level route issue rather than a Docker networking failure.

### Key Engineering Lessons

* Nginx can act as the public gateway while application services remain internal.
* Docker Compose provides service-to-service networking and DNS.
* Service names are more reliable than hardcoded container IP addresses.
* `depends_on` controls startup ordering but does not establish application readiness.
* A successful network connection does not guarantee that the requested application route exists.

### Sprint 4 Outcome

OpsBoard evolved from a single container into a multi-container architecture with Nginx acting as the public reverse proxy and Flask operating as an internal backend service.

---

## Sprint 5 — Database Integration & Multi-Service Architecture

### Objective

Replace temporary in-memory incident data with persistent MySQL storage and establish a stateful multi-service application architecture.

### Architecture

OpsBoard evolved into:

```text
Browser
   ↓ HTTP :80
Nginx reverse proxy
   ↓ backend:8000
Flask REST API
   ↓ mysql:3306
MySQL 8.0
   ↓
Docker named volume
```

Only Nginx publishes a host port.

```text
Host :80  → Nginx :80
```

The Flask and MySQL ports remain internal to the Docker network:

```text
Flask :8000
MySQL :3306
```

### Database

Added:

```text
mysql:8.0
```

and the Python dependency:

```text
mysql-connector-python==9.4.0
```

Created the `incidents` table with:

* `id`
* `title`
* `status`
* `severity`

The previous in-memory incident data was replaced with database-backed incident retrieval.

### Persistent Storage

Added a Docker named volume:

```text
opsboard_mysql_data
```

mounted at:

```text
/var/lib/mysql
```

This separated the lifecycle of the database data from the lifecycle of the MySQL container.

The key operational distinction established was:

> Containers can be replaced; persistent data should survive container replacement.

### Database Configuration

Database configuration was moved into environment variables.

The backend receives:

```text
DB_HOST
DB_PORT
DB_NAME
DB_USER
DB_PASSWORD
```

The MySQL service receives its database initialization credentials through environment variables as well.

A `.env.example` file was added as a safe configuration template.

Real `.env` files were excluded from Git using `.gitignore`.

### Service Discovery

The Flask backend connects to MySQL using:

```text
mysql
```

as the hostname rather than a hardcoded container IP.

Docker Compose DNS resolves the service name to the current MySQL container.

This protects the application from depending on an ephemeral container IP.

### Database Readiness

A MySQL health check was added using:

```text
mysqladmin ping
```

The backend was configured to depend on MySQL becoming healthy:

```yaml
depends_on:
  mysql:
    condition: service_healthy
```

This established an important distinction:

> A container being started is not the same thing as its service being ready.

### Persistence and API Testing

Verified that the database contained the expected incident:

```text
Database Connection Timeout
```

with:

```text
status: investigating
severity: high
```

Verified successful retrieval through the API.

Also verified that requesting a nonexistent incident ID returned:

```text
404 Not Found
```

### Network Boundary

The final Sprint 5 network boundary was:

```text
                    PUBLIC
                       │
                    :80
                       │
                    Nginx
                       │
                Docker network
                 ┌─────┴─────┐
                 │           │
              Flask        MySQL
              :8000         :3306
                 │           │
                 └───────────┘
```

Flask and MySQL were not directly published to the host.

### Security and Configuration Hygiene

Added:

```text
.env
```

to `.gitignore` while preserving:

```text
.env.example
```

This established the separation between:

* configuration templates that can be committed;
* real environment configuration containing secrets.

### Key Engineering Lessons

* Application state should not depend on a container's writable filesystem.
* Docker volumes provide persistence across container replacement.
* Service discovery should use Compose service names rather than container IP addresses.
* `depends_on` with `service_healthy` provides dependency readiness during startup.
* Health checks are different from simply checking whether a container is running.
* Internal services do not need to expose their ports to the host.
* Secrets and configuration should be supplied through the environment rather than hardcoded into application or Compose files.
* Multi-service architecture requires reasoning about both application behavior and infrastructure behavior.

### Release

Sprint 5 was released as:

```text
v0.4.0 — Database Integration & Multi-Service Architecture
```

with commit:

```text
1620c48 feat: integrate MySQL persistence
```

### Sprint 5 Outcome

OpsBoard became a stateful, multi-service application with:

* Nginx reverse proxy
* Flask REST API
* MySQL 8.0
* Docker Compose networking
* service-name DNS
* persistent database storage
* environment-based configuration
* MySQL health checks
* dependency readiness handling
* a controlled public network boundary

---

## Sprint 6 — Operational Robustness

### Objective

Improve OpsBoard's behavior when the database becomes unavailable and establish predictable API failure semantics.

### Problem Discovered

When the MySQL container was stopped, requests to the incident endpoints produced an HTTP 500 response and exposed Flask's development error page.

The failure occurred while the backend attempted to establish a connection to the MySQL service.

This revealed two operational weaknesses:

1. Database failures were not translated into an appropriate API response.
2. Database resources were manually closed, which could leave cleanup code unreachable if an exception occurred before the cleanup statements.

### Engineering Changes

#### 1. Database Resource Management

Refactored database access to use Python context managers:

```python
with get_db_connection() as connection:
    with connection.cursor(dictionary=True) as cursor:
        ...
```

Both incident endpoints now use the same resource-management pattern.

#### 2. Centralized Database Error Handling

Added a centralized Flask error handler for MySQL connector exceptions.

Database failures now return:

```text
HTTP 503 Service Unavailable
```

with a safe JSON response:

```json
{
    "error": "Service Unavailable",
    "message": "The database is currently unavailable."
}
```

Detailed database errors are logged server-side rather than returned to API clients.

This separates:

* Client-facing error information
* Internal diagnostic information

#### 3. API Failure Semantics

OpsBoard now distinguishes between different failure conditions:

| Condition                         | HTTP Status |
| --------------------------------- | ----------: |
| Requested incident exists         |         200 |
| Requested incident does not exist |         404 |
| Database unavailable              |         503 |

### Failure Testing

The MySQL container was intentionally stopped while Nginx and the backend remained running.

The API returned:

```text
503 Service Unavailable
```

with the expected JSON error response.

The behavior was verified for:

```text
GET /api/incidents
GET /api/incidents/1
```

### Recovery Testing

MySQL was restarted without restarting the backend.

After MySQL became healthy again, requests successfully returned:

```text
200 OK
```

This demonstrated that the backend can recover from a temporary database outage because each request establishes a database connection when needed.

### Key Engineering Lessons

* A running container does not mean its dependencies are available.
* Resource cleanup should not depend on the success path.
* `with` manages resource lifecycle; error handlers manage failure responses.
* HTTP status codes should communicate the actual class of failure.
* Internal infrastructure errors should not unnecessarily leak to API clients.
* Failure testing is as important as happy-path testing.
* Recovery behavior should be tested explicitly rather than assumed.

### Sprint 6 Outcome

OpsBoard now has predictable database failure behavior, safer error responses, consistent database resource management, server-side diagnostics, and verified recovery from a database outage.

## Sprint 7 — CI/CD & Release Engineering

### Objective

Build an automated delivery workflow for OpsBoard that validates changes before merge, protects the `main` branch, publishes versioned backend container images, and provides a reproducible release environment that can bootstrap from a fresh database.

The sprint evolved through several stages:

```text
Pull Request
    ↓
Automated CI
    ↓
Protected main
    ↓
Release gate
    ↓
Container registry
    ↓
Versioned release artifact
    ↓
Reproducible deployment
```

The goal was not simply to make GitHub Actions turn green.

The goal was to create evidence that a change can move safely from source code to a runnable release artifact.

---

### CI Foundation

A GitHub Actions workflow was introduced for both:

```text
pull_request → main
push → main
```

The first CI job, `backend-ci`, performs:

```text
Checkout repository
        ↓
Set up Python 3.12
        ↓
Install dependencies
        ↓
Compile Python source
        ↓
Run unit tests
        ↓
Build backend Docker image
```

The syntax validation step uses:

```text
python -m compileall backend
```

This catches Python syntax errors before later stages execute.

The Docker build step verifies that the backend can still be packaged successfully after application or dependency changes.

---

### Deliberate CI Failure Exercise

To verify that CI was actually capable of rejecting bad code, a deliberate syntax error was introduced on a feature branch:

```python
def intentional_ci_failure()
    return "This should fail CI"
```

The pull request failed during Python syntax validation with:

```text
SyntaxError: expected ':'
Process completed with exit code 1
```

The syntax error was corrected and pushed to the same branch.

GitHub Actions automatically reran the workflow and returned to green.

The experimental branch was then closed without allowing the intentionally broken version to reach `main`.

This established an important principle:

> CI should not only be configured. Its failure behavior should be deliberately verified.

---

### Unit Testing

Python `unittest` was introduced to validate application behavior independently of a real database.

The unit-test suite now verifies:

```text
GET /api/health
→ 200 OK

GET /api/health
→ expected JSON contract

GET /api/incidents
→ mocked database rows returned correctly

GET /api/incidents
→ database failure becomes 503

GET /api/incidents/<id>
→ database failure becomes 503
```

Database-dependent unit tests use `unittest.mock` to replace `get_db_connection()` with controlled behavior.

This allows the tests to answer questions such as:

> If the database layer raises `mysql.connector.Error`, does the application translate that failure into the correct HTTP response?

The unit tests therefore isolate application behavior from infrastructure behavior.

---

### Unit Tests vs. Integration Tests

An important testing distinction was established during this sprint.

A unit test using a mocked database can prove application logic, but it cannot prove that:

* SQL syntax is valid.
* The schema matches application expectations.
* `mysql.connector` can communicate with an actual MySQL server.
* Queries behave correctly against a real database engine.

This led to a second CI job:

```text
integration-tests
```

The integration job starts a real:

```text
mysql:8.0
```

service container inside GitHub Actions.

The GitHub-hosted runner connects to MySQL through:

```text
127.0.0.1:3306
```

because the Python test process runs directly on the runner while the MySQL service container publishes port `3306` to that runner.

This differs from Docker Compose, where the Flask backend runs inside another container and therefore connects using:

```text
mysql:3306
```

through Docker DNS.

This reinforced the principle:

> The correct hostname depends on where the client process is running.

---

### Integration Test Lifecycle

The MySQL integration tests create deterministic database state:

```text
connect
   ↓
create schema if required
   ↓
truncate previous rows
   ↓
seed known test rows
   ↓
run API tests
   ↓
truncate test data
   ↓
close connection
```

The integration suite verifies:

```text
GET /api/incidents
→ 200 with real MySQL rows

GET /api/incidents/1
→ 200 with the expected incident

GET /api/incidents/999
→ 404 Not Found
```

The test data is controlled rather than relying on whatever data may already exist in a database.

This established another important principle:

> Integration tests should use real infrastructure with controlled test data, not uncontrolled production data.

---

### Database Resource-Management Refactor

The single-incident endpoint originally opened its connection and cursor manually.

It was refactored to use nested context managers:

```python
with get_db_connection() as connection:
    with connection.cursor(dictionary=True) as cursor:
        ...
```

The external API contract remained unchanged.

Existing integration tests verified that:

```text
existing incident → 200
missing incident  → 404
```

still behaved correctly after the internal implementation changed.

An additional unit test was then added to verify:

```text
database failure → 503
```

for the single-incident endpoint.

This demonstrated the value of automated tests during refactoring:

> Internal implementation can change while externally observable behavior remains protected.

---

### CI Enforcement and Protected `main`

Initially, CI could report a failure but GitHub could still allow a merge.

A branch ruleset was therefore added to protect `main`.

The required checks are:

```text
backend-ci
integration-tests
```

Both must succeed before a pull request can be merged.

This changed CI from an advisory system:

```text
CI fails
→ developer is warned
```

into an enforcement mechanism:

```text
CI fails
→ merge is blocked
```

The release-only job is intentionally not required on pull requests because it does not run until code reaches `main`.

---

### Release Gate

A third job was introduced:

```text
publish-image
```

It declares:

```yaml
needs:
  - backend-ci
  - integration-tests
```

and runs only when:

```text
event = push
branch = main
```

The resulting control flow is:

```text
Pull Request
    ↓
backend-ci ✅
integration-tests ✅
publish-image ⏭ skipped
    ↓
merge allowed
```

After the merge:

```text
push to main
    ↓
backend-ci ✅
integration-tests ✅
    ↓
publish-image ✅
```

This ensures that proposed code can be tested without being allowed to publish a release artifact.

Only validated code on trusted `main` can publish.

---

### GitHub Container Registry

The release job publishes the backend image to GitHub Container Registry.

Authentication uses the workflow-provided GitHub token rather than a manually stored registry password.

The publishing job is limited to:

```text
contents: read
packages: write
```

This keeps package-writing permission scoped only to the job that actually requires it.

Two image tags are produced:

```text
ghcr.io/wondwossenh9/opsboard-backend:<git-commit-sha>

ghcr.io/wondwossenh9/opsboard-backend:latest
```

The `latest` tag provides convenience.

The commit-SHA tag provides traceability between source code and the container artifact.

The distinction established was:

```text
latest
→ moving reference

Git SHA tag
→ traceable source revision

image digest
→ exact image content
```

---

### External Artifact Verification

Publishing successfully from CI was not treated as sufficient evidence.

The SHA-tagged image was pulled manually from GHCR:

```text
docker pull ghcr.io/wondwossenh9/opsboard-backend:<commit-sha>
```

The pull returned a container digest, proving that the registry artifact could be retrieved independently of the temporary CI runner.

The image was then started locally and tested.

Without MySQL:

```text
GET /api/health
→ 200 OK

GET /api/incidents
→ 503 Service Unavailable
```

This demonstrated that the application itself remained available while its database dependency was unavailable.

The same exact image was then connected to an existing MySQL service through Docker networking and runtime environment configuration.

Without rebuilding the image:

```text
GET /api/incidents
→ 200 OK
```

This demonstrated:

> Build once. Configure at runtime.

---

### Release Compose Configuration

Development Compose originally built the backend directly from local source:

```yaml
backend:
  build:
    context: ./backend
```

A separate release configuration was introduced:

```text
compose.release.yaml
```

The release backend uses:

```yaml
backend:
  image: ${BACKEND_IMAGE:?BACKEND_IMAGE must be set}
```

The deployment environment therefore consumes a previously published artifact instead of rebuilding application source.

This separates two workflows:

```text
Development
→ build local source
→ fast iteration
```

from:

```text
Release
→ pull exact tested image
→ run known artifact
```

This supports the stronger release principle:

> Build once, deploy the same artifact.

The release Compose stack is run under a separate project name:

```text
opsboard-release
```

which creates isolated resources such as:

```text
opsboard-release_default
opsboard-release_mysql_data
```

rather than accidentally reusing the development environment.

---

### Fresh Release Failure: Missing Database Schema

The isolated release environment was deliberately started with a completely fresh MySQL volume.

The infrastructure appeared healthy:

```text
MySQL    → healthy
Backend  → running
Nginx    → running
```

and:

```text
GET /api/health
→ 200 OK
```

However:

```text
GET /api/incidents
→ 503 Service Unavailable
```

Backend logs revealed:

```text
Table 'mydatabase.incidents' doesn't exist
```

This demonstrated that:

```text
database server exists
        ≠
application schema exists
```

The database was reachable, but the release process had no reproducible method for creating the schema.

---

### Version-Controlled Database Migration

Instead of manually creating the table inside the running database, the schema was added to the repository:

```text
db/
└── migrations/
    └── 001_create_incidents.sql
```

The migration creates:

```text
incidents
├── id
├── title
├── status
└── severity
```

A one-shot Compose service named:

```text
migrate
```

was introduced.

The startup dependency became:

```text
MySQL healthy
      ↓
migration runs
      ↓
migration exits successfully
      ↓
backend starts
      ↓
Nginx starts
```

The backend now depends on:

```yaml
condition: service_completed_successfully
```

for the migration service.

A successful migration is therefore expected to appear as:

```text
migrate → Exited (0)
```

rather than remaining as a long-running container.

---

### Migration Failure and Readiness Diagnosis

The first migration attempt failed:

```text
migrate → Exited (1)
backend → Created
nginx   → Created
```

Because the migration failed, Compose correctly prevented the backend and Nginx from starting.

Migration logs showed:

```text
Can't connect to MySQL server on 'mysql:3306'
```

even though MySQL had already been marked healthy.

The existing health check used:

```text
mysqladmin ping -h localhost
```

which could validate MySQL locally from inside its own container without proving the TCP readiness required by another container.

The health check was changed to explicitly test:

```text
--protocol=TCP
-h 127.0.0.1
```

After recreating the environment from scratch:

```text
MySQL    → Up (healthy)
migrate  → Exited (0)
backend  → Up
Nginx    → Up
```

and:

```text
GET /api/health
→ 200 OK

GET /api/incidents
→ 200 OK
```

with:

```json
{
    "incidents": [],
    "total": 0
}
```

The empty result was intentional.

The migration creates schema, not fake application data.

This established an important readiness principle:

> A health check should verify the capability that downstream services actually depend on.

---

### Production WSGI Runtime

Release testing exposed another issue in the backend logs:

```text
WARNING: This is a development server.
Debug mode: on
Debugger is active!
```

The backend container was still starting with:

```text
python app.py
```

which executed Flask's development server.

Gunicorn was introduced as the production WSGI runtime.

The backend dependency list now includes:

```text
gunicorn==26.2.0
```

and the Docker container starts with:

```text
gunicorn
--bind 0.0.0.0:8000
--workers 2
--access-logfile -
--error-logfile -
app:app
```

The runtime architecture is now:

```text
Client
   ↓
Nginx
   ↓
Gunicorn
   ↓
Flask application
   ↓
MySQL
```

Gunicorn logs are written to the container's stdout and stderr so they remain visible through Docker logging.

---

### Gunicorn Verification

The Gunicorn change was first tested with a temporary local image.

Runtime logs verified:

```text
Starting gunicorn 26.2.0
Listening at: http://0.0.0.0:8000
Using worker: sync
Booting worker with pid ...
Booting worker with pid ...
```

Two workers started as configured.

The Flask development-server warning, debugger, and reloader were no longer present.

The health endpoint returned:

```text
200 OK
Server: gunicorn
```

The database failure path was also deliberately tested without MySQL configuration:

```text
GET /api/incidents
→ 503 Service Unavailable
```

while Gunicorn logs retained the detailed MySQL connection error.

This verified that changing the production runtime did not break the centralized database error contract.

---

### Final Release Verification

After the Gunicorn change was merged, CI again required:

```text
backend-ci ✅
integration-tests ✅
```

before:

```text
publish-image ✅
```

A new SHA-tagged GHCR image was published.

The release environment was destroyed completely, including its MySQL volume, and recreated from scratch using the new artifact.

The final startup state was:

```text
mysql      → Up (healthy)
migrate    → Exited (0)
backend    → Up
nginx      → Up
```

The backend process was confirmed to be Gunicorn.

Through Nginx:

```text
GET /api/health
→ 200 OK

GET /api/incidents
→ 200 OK
```

Backend logs confirmed:

```text
Gunicorn master running
two workers booted
health request → 200
incident request → 200
```

No Flask development-server or debugger messages were present.

---

### Final Sprint 7 Delivery Flow

OpsBoard's delivery path is now:

```text
Developer
    ↓
feature branch
    ↓
Pull Request
    ↓
┌────────────────────┐
│ backend-ci         │
│ integration-tests  │
└────────────────────┘
    ↓
both required
    ↓
protected main
    ↓
push event
    ↓
CI reruns
    ↓
release gate
    ↓
build backend image
    ↓
publish to GHCR
    ↓
SHA-tagged artifact
    ↓
release Compose
    ↓
MySQL
    ↓
database migration
    ↓
Gunicorn backend
    ↓
Nginx
    ↓
HTTP traffic
```

---

### Security and Operational Improvements

Sprint 7 established:

* Protected `main` with required CI status checks.
* Pull-request validation before merge.
* Package publication only from trusted `main`.
* Job-scoped `packages: write` permission.
* No hardcoded registry credentials.
* Runtime configuration separated from the container image.
* `.env` excluded from version control.
* SHA-tagged release artifacts for traceability.
* Isolated release networks and database volumes.
* Database migration gating before application startup.
* Production WSGI serving through Gunicorn.
* Container logs written to stdout/stderr for operational visibility.

---

### Key Engineering Lessons

* CI should be deliberately tested in both success and failure states.
* A successful Docker build does not prove that an application behaves correctly.
* Unit tests and integration tests answer different questions and should complement one another.
* Real infrastructure tests should use controlled test data.
* CI becomes significantly more valuable when failed checks actually block merges.
* Proposed code should be testable without being allowed to publish release artifacts.
* Release artifacts should be traceable back to source commits.
* `latest` is convenient but is not a precise rollback target.
* Container image digests identify exact image content.
* A registry artifact should be pulled and executed from the consumer side, not merely trusted because a push step succeeded.
* Deployment environments should consume tested artifacts instead of rebuilding application source.
* Environment configuration should be supplied at runtime.
* A healthy database server does not imply that the required application schema exists.
* Database schema changes should be version-controlled and reproducible.
* One-shot migration jobs should succeed before dependent application services start.
* Health checks should test the capability required by downstream consumers.
* `Exited (0)` can represent successful completion for one-shot jobs.
* Production containers should run production application servers rather than development servers.
* Application behavior should be reverified after changing the runtime layer.
* A deployment should be reproducible from a clean environment rather than depending on undocumented machine state.

---

### Sprint 7 Outcome

OpsBoard progressed from a manually operated container stack into a CI-controlled release workflow with:

* GitHub Actions CI
* protected pull-request workflow
* 5 unit tests
* 3 real-MySQL integration tests
* Docker build validation
* enforced status checks
* gated container publishing
* GitHub Container Registry
* Git-SHA-tagged release artifacts
* external artifact verification
* isolated release orchestration
* version-controlled database migration
* dependency-aware startup
* TCP-aware MySQL readiness
* Gunicorn production WSGI serving
* verified fresh-environment deployment

The project can now take a source change through automated validation and produce a traceable container artifact that can bootstrap successfully in an isolated release environment.

Sprint 7 prepares OpsBoard for the next major phase:

```text
AWS deployment
        ↓
Terraform infrastructure as code
        ↓
Kubernetes orchestration
        ↓
observability and final production hardening
```
