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

## Sprint 8 — AWS Deployment, Observability & Alerting

### Objective

Deploy the existing OpsBoard release artifact to AWS, understand the infrastructure manually before introducing Terraform, verify security boundaries, observe failure behavior, and build an operational monitoring and alerting loop.

The sprint followed this progression:

```text
VPC
  ↓
subnets
  ↓
routing
  ↓
security groups
  ↓
RDS
  ↓
EC2
  ↓
Docker runtime
  ↓
Application Load Balancer
  ↓
CloudWatch metrics
  ↓
CloudWatch alarms
  ↓
SNS notifications
```

The goal was not only to make OpsBoard reachable from the Internet.

The goal was to understand how each infrastructure layer behaves, how failures propagate, and how AWS telemetry can be used to diagnose them.

---

### Manual Infrastructure Before Terraform

Sprint 8 deliberately used manually created AWS resources.

Terraform was postponed until the next sprint so the underlying AWS concepts could be understood first.

The learning sequence was:

```text
understand the resource
        ↓
create it manually
        ↓
verify behavior
        ↓
break it deliberately
        ↓
observe failure
        ↓
recover it
        ↓
document the lesson
        ↓
encode it later with Terraform
```

This avoids treating Infrastructure as Code as a way to automate architecture that is not yet understood.

---

### AWS CLI Authentication

The local AWS CLI originally contained stale static credentials.

The old credentials file was preserved as a backup and removed from active use.

Authentication was moved to the newer browser-based AWS CLI login flow using the IAM administrator identity.

The CLI was upgraded to a current AWS CLI v2 release before continuing.

This reinforced the principle:

> Authentication problems should be resolved before infrastructure troubleshooting begins.

---

### Cost Controls

The AWS account was treated as a metered engineering lab.

A monthly AWS Budget was configured.

The deployment was designed to avoid unnecessary recurring charges.

Choices included:

```text
no NAT Gateway
t3.micro EC2
db.t4g.micro RDS
Single-AZ database
small gp3 volumes
native CloudWatch metrics
```

EC2 and RDS were stopped during periods when the lab was not being used.

A key lesson was that an Application Load Balancer cannot be stopped.

To stop its hourly charges, it must be deleted.

This made cost management part of normal operational thinking rather than a separate billing exercise.

---

### VPC Architecture

A dedicated VPC was created:

```text
10.0.0.0/16
```

Four subnets were created across two Availability Zones:

```text
Public A      10.0.1.0/24
Public B      10.0.2.0/24

DB Private A  10.0.11.0/24
DB Private B  10.0.12.0/24
```

An Internet Gateway was attached to the VPC.

The public route table contains:

```text
0.0.0.0/0
→ Internet Gateway
```

The private database route table contains only the VPC-local route.

This established the distinction:

```text
Public subnet
→ route to an Internet Gateway

Private subnet
→ no direct Internet default route
```

It also reinforced that subnet type is determined by routing behavior rather than by the subnet name.

---

### Route Tables vs. Security Groups

An important networking distinction was reinforced during the sprint.

```text
Route table
→ where can the packet go?

Security group
→ is the packet allowed?
```

A valid route does not imply that traffic is permitted.

A permissive security group does not create a missing route.

Troubleshooting therefore needs to consider both layers independently.

---

### Security-Group Design

Three security groups were created.

The intended trust path is:

```text
Internet
    ↓
ALB Security Group
    ↓
EC2 Security Group
    ↓
RDS Security Group
```

The ALB allows:

```text
TCP 80
source: Internet
```

The EC2 application host allows:

```text
TCP 80
source: ALB security group
```

The RDS database allows:

```text
TCP 3306
source: EC2 security group
```

Security-group references were preferred over broad CIDR rules.

This means the database trusts the application tier rather than every resource inside the VPC.

---

### RDS Deployment

Amazon RDS MySQL was deployed using:

```text
MySQL 8.0
db.t4g.micro
Single-AZ
20 GiB gp3
encrypted storage
publicly accessible: false
```

The database subnet group spans the two private database subnets.

The database name is:

```text
mydatabase
```

The RDS endpoint remained private and was accessed only from the application tier.

---

### Progressive Database Connectivity Testing

Database connectivity was tested layer by layer instead of jumping directly to the Flask application.

The sequence was:

```text
DNS resolution
    ↓
TCP 3306
    ↓
MySQL authentication
    ↓
database existence
    ↓
schema existence
    ↓
application query
```

The EC2 host successfully resolved the RDS endpoint.

TCP connectivity to port `3306` succeeded.

A temporary MySQL Docker client authenticated successfully.

The MySQL server version was verified.

The application database existed.

Initially, the database contained no application table.

This isolated connectivity from schema state.

---

### Migration Troubleshooting

The existing Sprint 7 SQL migration was applied to RDS.

The first migration attempt failed with:

```text
using password: NO
```

This was initially a useful diagnostic clue.

The error did not indicate:

```text
wrong security group
wrong route table
wrong RDS endpoint
```

It indicated that the client process had not actually received a password.

The environment variable was corrected and the migration succeeded.

Afterward:

```text
SHOW TABLES
→ incidents
```

The schema structure was verified and the initial row count was zero.

This reinforced:

> Authentication errors should not automatically be treated as networking errors.

---

### EC2 Application Host

An EC2 `t3.micro` instance was launched in the public application subnet.

Ubuntu Server 24.04 LTS x86_64 was selected.

The x86_64 architecture was chosen because the existing GitHub Container Registry image had been built on an x86_64 GitHub-hosted runner.

Using an ARM instance without a multi-architecture container image could have introduced an image architecture mismatch.

The EC2 instance uses:

```text
8 GiB encrypted gp3
IMDSv2 required
T3 CPU credits: standard
```

No SSH key was required.

Administration uses AWS Systems Manager Session Manager.

---

### Systems Manager Administration

An IAM role and instance profile were created for EC2.

The role includes:

```text
AmazonSSMManagedInstanceCore
```

The EC2 instance successfully registered with Systems Manager.

The local Session Manager plugin was installed on Ubuntu.

Administrative access then used:

```text
aws ssm start-session
```

No inbound port `22` was opened.

This established the operating model:

```text
Provisioning plane
Ubuntu workstation + AWS CLI

Runtime plane
EC2 + Docker + application
```

The AWS CLI was not required inside EC2.

---

### Docker Runtime on EC2

Docker and Docker Compose were installed on EC2.

A dedicated Docker bridge network was created for OpsBoard.

The backend container was deployed using the exact Sprint 7 Git-SHA-tagged GHCR image.

This preserved the release principle:

```text
build once
    ↓
publish
    ↓
deploy the same artifact
```

The backend was started with:

```text
--restart unless-stopped
```

and published only to:

```text
127.0.0.1:8000
```

The backend therefore remained inaccessible directly from the Internet.

Runtime database configuration was stored in:

```text
/etc/opsboard/backend.env
```

with restrictive root-only permissions.

No secret was committed to Git.

---

### Nginx Deployment

The Nginx image was rebuilt on EC2 using the Sprint 7 configuration.

Nginx joined the same Docker network as the backend.

The backend container had the network alias:

```text
backend
```

which allowed Nginx to proxy to:

```text
backend:8000
```

Nginx exposed host port `80`.

Local EC2 verification returned:

```text
GET /api/health
→ 200 OK

GET /api/incidents
→ 200 OK
```

The local application path was therefore:

```text
Nginx
    ↓
Docker DNS
    ↓
Gunicorn
    ↓
Flask
    ↓
RDS MySQL
```

---

### Application Load Balancer

An Internet-facing Application Load Balancer was created across the two public subnets.

The listener uses:

```text
HTTP :80
```

and forwards traffic to a target group on:

```text
EC2 :80
```

The health check path is:

```text
/api/health
```

The EC2 instance was registered as the target.

The target transitioned from:

```text
initial
```

to:

```text
healthy
```

after successful health checks.

Public requests then succeeded:

```text
GET /api/health
→ 200 OK

GET /api/incidents
→ 200 OK
```

---

### Security-Boundary Test

The EC2 instance had a public IPv4 address.

A deliberate test attempted to bypass the ALB and connect directly:

```text
http://EC2_PUBLIC_IP/api/health
```

The request timed out.

At the same time:

```text
http://ALB_DNS/api/health
```

returned:

```text
200 OK
```

This proved:

```text
Internet → EC2 directly
→ blocked

Internet → ALB → EC2
→ allowed
```

The EC2 public IP alone did not bypass the security-group trust model.

---

### Deliberate Nginx Failure

Nginx was intentionally stopped while:

```text
backend remained running
RDS remained available
```

This isolated the reverse-proxy layer.

The ALB eventually marked the target:

```text
unhealthy
```

with:

```text
Target.FailedHealthChecks
```

CloudWatch showed:

```text
HealthyHostCount
→ decreased

UnHealthyHostCount
→ increased
```

During the failure:

```text
TargetConnectionErrorCount
→ increased
```

and the ALB produced:

```text
HTTP 502
```

This provided a clear failure chain:

```text
ALB selects target
    ↓
connection to Nginx fails
    ↓
TargetConnectionErrorCount
    ↓
ALB 502
```

---

### Longer Backend Unavailability

The infrastructure was later left without a usable backend for a longer period.

The public ALB continued receiving traffic.

CloudWatch recorded repeated:

```text
HTTPCode_ELB_503_Count
```

events.

Some five-minute periods contained large request bursts.

These were not ALB health checks because health-check traffic is not counted in the normal HTTP response metrics.

The traffic demonstrated that a public Internet endpoint can receive unsolicited automated requests even when the DNS name has not been deliberately advertised.

The exact request sources were not determined because ALB access logging was outside the scope of this sprint.

---

### 502 vs. 503

Sprint 8 provided a practical distinction between two ALB failure modes.

```text
502
→ ALB selected the target
→ communication with the backend failed
```

```text
503
→ ALB had no usable target available
```

The distinction was observed through real CloudWatch metrics rather than only studied theoretically.

---

### CloudWatch ALB Observability

ALB metrics examined included:

```text
HealthyHostCount
UnHealthyHostCount
RequestCount
HTTPCode_Target_2XX_Count
HTTPCode_Target_4XX_Count
HTTPCode_Target_5XX_Count
HTTPCode_ELB_502_Count
HTTPCode_ELB_503_Count
TargetConnectionErrorCount
TargetResponseTime
```

The historical data clearly captured the deliberate failure and recovery.

This demonstrated the distinction between:

```text
Health checks
→ Is the target usable now?

Metrics
→ How did behavior change over time?

Logs
→ What happened inside the application?
```

---

### RDS Observability

RDS metrics examined included:

```text
DatabaseConnections
CPUUtilization
FreeableMemory
FreeStorageSpace
CPUCreditBalance
CPUSurplusCreditBalance
CPUSurplusCreditsCharged
SwapUsage
```

The database showed low steady-state CPU usage.

Free storage remained high.

Freeable memory was relatively small but stable.

Swap usage remained negligible.

---

### Database Connection Metric Experiment

Initially:

```text
DatabaseConnections = 0
```

even though application database requests were known to work.

A deliberately long-lived MySQL session was created.

A later CloudWatch query showed:

```text
DatabaseConnections = 1
```

during the connection period.

This demonstrated that metric publication timing matters.

A recently occurring event may not be immediately visible through CloudWatch.

The correct operational response is to verify the underlying system before assuming the monitoring platform is wrong.

---

### RDS CPU Credit Behavior

After the RDS instance restarted:

```text
CPUCreditBalance
→ initially 0
```

A small:

```text
CPUSurplusCreditBalance
```

was observed during startup.

As CPU utilization settled, the normal credit balance increased and the surplus balance returned to zero.

Most importantly:

```text
CPUSurplusCreditsCharged = 0
```

throughout the observation window.

The temporary surplus credits were repaid rather than becoming billable surplus usage.

This connected performance telemetry directly to cost awareness.

---

### EC2 Observability

EC2 metrics examined included:

```text
CPUUtilization
CPUCreditBalance
StatusCheckFailed_Instance
StatusCheckFailed_System
```

CPU utilization remained extremely low under the current workload.

The CPU credit balance steadily increased.

Both status-check metrics remained:

```text
0
```

throughout the observation window.

This created an important diagnostic distinction.

During the Nginx failure:

```text
application health
→ failed

EC2 infrastructure health
→ remained healthy
```

Therefore:

```text
ALB unhealthy + EC2 healthy
```

points investigation toward the application/runtime layer rather than the EC2 host or AWS physical infrastructure.

---

### CloudWatch Alarms

Three alarms were created:

```text
opsboard-alb-unhealthy-target
opsboard-ec2-status-check-failed
opsboard-rds-low-storage
```

The ALB alarm monitors:

```text
UnHealthyHostCount
```

using:

```text
period: 60 seconds
evaluation periods: 2
datapoints to alarm: 2
threshold: >= 1
```

A single brief unhealthy datapoint therefore does not immediately transition the alarm into `ALARM`.

---

### Deliberate Alarm Trigger

Nginx was stopped again specifically to validate the alarm.

The metric changed:

```text
UnHealthyHostCount
0
→ 1
```

for consecutive periods.

CloudWatch then changed:

```text
OK
→ ALARM
```

The alarm reason explicitly showed two consecutive breaching datapoints.

After Nginx restarted:

```text
EC2-local health
→ 200 OK

ALB target
→ healthy

UnHealthyHostCount
→ 0
```

and CloudWatch returned:

```text
ALARM
→ OK
```

This verified both detection and recovery behavior.

---

### SNS Alerting

An SNS topic was created for OpsBoard alerts.

An email subscription was added and confirmed.

Before integrating with CloudWatch, SNS was tested independently.

The test email arrived successfully.

The ALB alarm was then configured with:

```text
alarm-actions
ok-actions
```

both targeting the SNS topic.

This enabled failure and recovery notifications.

---

### Notification Verification

CloudWatch alarm history recorded successful SNS action execution for both:

```text
ALARM
OK
```

state changes.

SNS metrics were then checked:

```text
NumberOfMessagesPublished
NumberOfNotificationsDelivered
NumberOfNotificationsFailed
```

The failure and recovery notifications both showed:

```text
published = 1
delivered = 1
failed = 0
```

This established an evidence-based notification chain:

```text
CloudWatch state transition
        ↓
SNS publish
        ↓
SNS delivery
        ↓
email endpoint
```

The monitoring system was therefore verified beyond merely observing an alarm state in the console.

---

### Operational Troubleshooting Pattern

Sprint 8 reinforced the troubleshooting method:

```text
Observe
    ↓
identify failing layer
    ↓
verify dependency beneath it
    ↓
repair only the failed layer
    ↓
verify outward toward the user
```

For the Nginx failure:

```text
Nginx state
    ↓
EC2-local /api/health
    ↓
ALB target health
    ↓
CloudWatch metric
    ↓
CloudWatch alarm
    ↓
public endpoint
```

The complete stack was not restarted blindly.

Only the failed layer was repaired.

---

### Shell Variables and Durable Resource Discovery

Several local shell variables disappeared between terminal sessions.

This caused commands to fail when variables such as:

```text
INSTANCE_ID
TARGET_GROUP_ARN
```

were empty.

The AWS resources themselves still existed.

The correct recovery pattern was:

```text
discover resource by tag or name
    ↓
restore shell variable
```

rather than guessing identifiers.

This established:

```text
AWS resource
→ durable

shell variable
→ temporary
```

Terraform will reduce much of this manual identifier bookkeeping in the next sprint.

---

### Cost-Aware Operating Pattern

The lab operating pattern became:

```text
build
    ↓
verify
    ↓
observe
    ↓
document
    ↓
stop or delete expensive resources
```

This is especially important for:

```text
Application Load Balancer
RDS
EC2
public IPv4
storage
```

The lesson was that cost management should be part of system operations rather than an afterthought.

---

### Current Limitations

Sprint 8 is intentionally not presented as a production-complete architecture.

Current limitations include:

```text
single EC2 application instance
Single-AZ RDS
HTTP rather than HTTPS
public application subnet
no Auto Scaling Group
no WAF
no centralized application logs
manual infrastructure provisioning
host-managed application secret file
```

These limitations define the next engineering opportunities rather than invalidating the learning deployment.

---

### Final Sprint 8 Architecture

```text
Internet
    ↓
Application Load Balancer
    ↓
ALB Security Group
    ↓
EC2 Security Group
    ↓
Nginx
    ↓
Gunicorn
    ↓
Flask
    ↓
RDS Security Group
    ↓
Amazon RDS MySQL
```

Operations add:

```text
ALB metrics
EC2 metrics
RDS metrics
      ↓
CloudWatch
      ↓
CloudWatch alarms
      ↓
Amazon SNS
      ↓
email notification
```

Administration uses:

```text
Ubuntu workstation
      ↓
AWS CLI
      ↓
Systems Manager
      ↓
EC2
```

---

### Key Engineering Lessons

* Manual infrastructure work is valuable when the objective is to understand the resources that will later be automated.
* Public routing and traffic permission are different networking concerns.
* Security-group references create useful trust boundaries between tiers.
* A public IPv4 address does not override security-group restrictions.
* Infrastructure failures should be isolated by layer.
* Database reachability, authentication, schema state, and application behavior are separate diagnostic domains.
* ALB `502` and `503` errors can indicate different failure conditions.
* Application health and EC2 infrastructure health are not the same thing.
* CloudWatch metrics can reconstruct incidents after they occur.
* Metric publication can lag behind the event being observed.
* CPU credits are both a performance and cost signal on burstable instances.
* Monitoring without tested alarms is incomplete.
* Alerting without tested notification delivery is incomplete.
* Repair should target the failed component rather than restart the entire system.
* Internet-facing infrastructure should be assumed to receive unsolicited traffic.
* Cost control is part of DevOps operations.

---

### Sprint 8 Outcome

OpsBoard progressed from a locally reproducible release artifact into a manually deployed AWS application with:

* dedicated VPC networking;
* public and private subnet separation;
* security-group tier isolation;
* private managed MySQL;
* EC2-hosted container runtime;
* SSM-based administration;
* Application Load Balancer ingress;
* verified security boundaries;
* native AWS observability;
* failure telemetry;
* CloudWatch alarms;
* SNS email notifications;
* recovery verification;
* AWS cost controls.

The project now demonstrates not only how to deploy a containerized application to AWS, but how to reason about its network path, security boundary, infrastructure health, application health, failure modes, telemetry, alerts, recovery, and cost.

Sprint 9 will take the manually understood architecture and reproduce it using Terraform:

```text
manual AWS infrastructure
        ↓
understood architecture
        ↓
Terraform
        ↓
repeatable infrastructure
        ↓
controlled change
        ↓
safe destruction and recreation
```

---

# Sprint 9 — Terraform Infrastructure as Code

## Objective

Sprint 8 established the OpsBoard AWS architecture manually.

The purpose of Sprint 9 was not to invent a different architecture.

The purpose was to take the infrastructure that had already been understood operationally and convert it into reproducible Infrastructure as Code using Terraform.

The target lifecycle was:

```text
terraform apply
        ↓
working OpsBoard environment
        ↓
terraform plan
        ↓
no drift
        ↓
terraform destroy
        ↓
infrastructure removed
        ↓
terraform apply
        ↓
working OpsBoard environment again
```

The sprint would not be considered complete merely because:

```text
terraform apply
```

successfully created AWS resources once.

The stronger goal was to prove:

```text
same configuration
        ↓
destroy existing environment
        ↓
create completely new AWS resources
        ↓
recover the same architecture
        ↓
recover the same application behavior
```

This changed the focus from:

```text
Can Terraform create infrastructure?
```

to:

```text
Is the infrastructure genuinely reproducible?
```

---

## Why Terraform Came After Manual AWS Deployment

The Sprint 8 architecture was deliberately built manually before introducing Terraform.

That sequence made it possible to understand the purpose of each resource before automating it.

The manually understood path was:

```text
Internet
    ↓
Application Load Balancer
    ↓
EC2
    ↓
Nginx
    ↓
Gunicorn
    ↓
Flask
    ↓
Amazon RDS MySQL
```

Supporting infrastructure included:

```text
VPC
subnets
route tables
Internet Gateway
security groups
IAM
Systems Manager
CloudWatch
SNS
```

Without that understanding, Terraform could easily become a collection of copied resource blocks whose relationships were not understood.

The learning principle established was:

```text
understand manually
        ↓
model declaratively
        ↓
automate confidently
```

---

## Terraform Foundation

Terraform `1.16.x` was installed and the AWS provider was pinned to:

```text
~> 6.69
```

The provider lock file was committed:

```text
infrastructure/terraform/.terraform.lock.hcl
```

while local Terraform working files were excluded from version control.

The repository ignores:

```text
**/.terraform/*
*.tfstate
*.tfstate.*
*.tfplan
*.tfvars
*.tfvars.json
```

while retaining:

```text
.terraform.lock.hcl
terraform.tfvars.example
```

This established the distinction:

```text
configuration
→ version controlled

provider dependency lock
→ version controlled

real secrets
→ local only

Terraform state
→ local only in this sprint
```

Remote state remains a later improvement.

---

## Configuration, State, and Real Infrastructure

One of the first important Terraform concepts was the distinction between:

```text
Configuration
State
Real AWS infrastructure
```

They answer different questions.

```text
Configuration
→ What should exist?

State
→ What does Terraform believe it manages?

AWS
→ What actually exists?
```

This became especially important because Sprint 8 already had manually created AWS infrastructure.

Declaring:

```hcl
resource "aws_vpc" "opsboard" {
  ...
}
```

does not cause Terraform to automatically locate and adopt an existing VPC with the same name.

The important principle was:

```text
resource exists in AWS
        ≠
resource managed by Terraform
```

Existing resources would require explicit import if they were to become Terraform-managed.

For Sprint 9, clean recreation was chosen instead.

---

## Manual Infrastructure Teardown

Before the first real Terraform deployment, the manually created Sprint 8 environment was deliberately dismantled.

This was important because otherwise a successful Terraform deployment might only prove that Terraform could coexist with manually created infrastructure.

The goal was stronger:

```text
manual environment removed
        ↓
Terraform state initially empty
        ↓
Terraform configuration becomes source of truth
```

The manual teardown also reinforced dependency ordering.

Higher-level dependencies were removed before lower-level networking resources.

Examples included:

```text
CloudWatch / SNS
        ↓
target group
        ↓
EC2
        ↓
RDS
        ↓
IAM
        ↓
security groups
        ↓
subnets / route tables
        ↓
Internet Gateway
        ↓
VPC
```

Delete-verification errors such as:

```text
TargetGroupNotFound
DBInstanceNotFound
NoSuchEntity
InvalidInternetGatewayID.NotFound
InvalidVpcID.NotFound
```

were interpreted correctly as evidence of successful removal when checking resources that had intentionally been deleted.

The distinction established was:

```text
"not found" during creation
→ possible problem

"not found" while verifying deletion
→ often successful evidence
```

---

## Terraform Network Modeling

The first major Terraform layer reproduced the Sprint 8 network foundation.

The VPC uses:

```text
10.0.0.0/16
```

with four subnets:

```text
Public A      10.0.1.0/24
Public B      10.0.2.0/24

Private DB A  10.0.11.0/24
Private DB B  10.0.12.0/24
```

The public subnets share a route table containing:

```text
0.0.0.0/0
    ↓
Internet Gateway
```

The database subnets use a separate private route table without an Internet default route.

The architecture therefore preserves:

```text
ALB
→ public subnets

EC2
→ public application subnet

RDS
→ private DB subnets
```

No NAT Gateway was introduced because this remains a cost-conscious learning environment.

---

## Terraform References and the Dependency Graph

Manual AWS work required repeatedly discovering and copying identifiers such as:

```text
VPC IDs
subnet IDs
security-group IDs
instance IDs
target-group ARNs
RDS endpoints
```

Terraform replaces much of that bookkeeping with resource references.

For example:

```hcl
subnet_id = aws_subnet.public_a.id
```

and:

```hcl
vpc_id = aws_vpc.opsboard.id
```

and:

```hcl
target_id = aws_instance.app.id
```

The configuration expresses relationships rather than physical identifiers.

This creates a dependency graph.

Conceptually:

```text
VPC
 ↓
subnets
 ↓
security groups
 ↓
EC2 / RDS / ALB
```

Terraform uses those relationships for both creation and destruction ordering.

This was one of the strongest conceptual differences from the manual Sprint 8 workflow.

---

## Security Group Modeling

Three security groups were modeled:

```text
ALB
EC2
RDS
```

Ingress follows:

```text
Internet
    ↓ TCP 80
ALB SG
    ↓ TCP 80
EC2 SG
    ↓ TCP 3306
RDS SG
```

The EC2 ingress rule references the ALB security group.

The RDS ingress rule references the EC2 security group.

This preserves the trust boundaries established manually in Sprint 8.

The application host does not expose:

```text
SSH :22
Gunicorn :8000
```

to the Internet.

Administration continues through Systems Manager.

---

## IAM and Systems Manager

Terraform creates the EC2 IAM role and instance profile.

The EC2 role includes:

```text
AmazonSSMManagedInstanceCore
```

for Systems Manager connectivity.

A separate runtime-secret policy grants only:

```text
ssm:GetParameter
```

for the OpsBoard database-password parameter.

The intended permission path is:

```text
EC2
 ↓
instance profile
 ↓
OpsBoardEC2Role
 ↓
ssm:GetParameter
 ↓
/opsboard/db/password
```

A broad:

```text
ssm:* on *
```

permission was not used.

This preserved the least-privilege objective while still supporting automated runtime configuration.

---

## Terraform Secret Handling

Database credentials required particular care because Terraform state can contain values that should not be persisted.

The database password variable was defined as:

```text
sensitive
ephemeral
```

The RDS resource uses a write-only password argument.

The SSM SecureString parameter also uses a write-only value.

The resulting design is:

```text
local terraform.tfvars
        ↓
ephemeral db_password
        ├────────→ RDS
        |
        └────────→ SSM SecureString
                          ↓
                    EC2 retrieves
```

This was an important refinement of the common misconception:

```text
sensitive = hidden
```

does not necessarily mean:

```text
sensitive = absent from state
```

The stronger design uses ephemeral and write-only capabilities where supported.

The real:

```text
terraform.tfvars
```

remains ignored.

Only:

```text
terraform.tfvars.example
```

is committed.

---

## EC2 Modeling

Terraform creates a:

```text
t3.micro
```

EC2 application host using an Ubuntu x86_64 AMI.

The x86_64 architecture was selected deliberately because the existing GHCR backend image had already been built and verified for that architecture.

The instance uses:

```text
encrypted gp3 root volume
IMDSv2 required
standard CPU credits
public IPv4
Systems Manager instance profile
```

Although the instance is placed in a public subnet for this lab architecture, inbound HTTP is still restricted to the ALB security group.

A public subnet does not itself mean:

```text
publicly reachable application
```

Routing and security rules remain separate controls.

---

## RDS Modeling

Terraform creates private Amazon RDS MySQL.

The database configuration includes:

```text
MySQL 8.0
db.t4g.micro
20 GiB gp3
encrypted storage
Single-AZ
publicly accessible = false
```

The subnet group spans the two private database subnets.

The database remains deliberately destroyable for the learning environment:

```text
deletion protection = false
skip final snapshot = true
```

This would not be the normal production data-protection posture.

It exists here because Sprint 9 explicitly requires repeated destruction and recreation.

---

## Load Balancer Modeling

Terraform creates:

```text
Application Load Balancer
target group
listener
target attachment
```

The ALB spans both public subnets.

The target group health check uses:

```text
GET /api/health
```

with:

```text
HTTP
port 80
matcher 200
30-second interval
5-second timeout
2 healthy checks
2 unhealthy checks
```

The EC2 target is attached using:

```hcl
target_id = aws_instance.app.id
```

rather than a copied physical instance ID.

---

## Monitoring and Alerting

Sprint 8 monitoring resources were also modeled.

Terraform creates alarms for:

```text
ALB unhealthy target
EC2 status-check failure
RDS low free storage
```

The ALB alarm publishes:

```text
ALARM
```

and:

```text
OK
```

state changes to the SNS topic.

The SNS email endpoint remains a local input rather than repository configuration.

This reproduces the monitoring architecture already proven manually in Sprint 8.

---

## Automating the Application Runtime

A major design question was whether Terraform should only create AWS infrastructure or also make the EC2 host operational.

The sprint objective required:

```text
terraform apply
→ working OpsBoard
```

not:

```text
terraform apply
→ empty EC2 server
→ manually configure application
```

Therefore EC2 user data was introduced through:

```text
user-data.sh.tftpl
```

The bootstrap performs:

```text
install Docker
        ↓
install AWS CLI if required
        ↓
create protected configuration directory
        ↓
retrieve database password
        ↓
write runtime environment
        ↓
restore SQL migration
        ↓
restore Nginx configuration
        ↓
create Docker network
        ↓
pull backend image
        ↓
pull Nginx image
        ↓
pull MySQL client image
        ↓
apply RDS migration
        ↓
start backend
        ↓
start Nginx
        ↓
verify local application health
```

This converted:

```text
Terraform creates infrastructure
```

into:

```text
Terraform creates usable application infrastructure
```

---

## Reusing Repository-Owned Configuration

The existing Sprint 7 migration:

```text
db/migrations/001_create_incidents.sql
```

and Nginx configuration:

```text
nginx/nginx.conf
```

were already the project sources of truth.

Creating separate copies inside the Terraform directory would introduce duplication.

Instead Terraform reads those files and supplies them to the user-data template.

Conceptually:

```text
repository-owned file
        ↓
Terraform file()
        ↓
base64encode()
        ↓
templatefile()
        ↓
EC2 user data
        ↓
restored on host
```

This keeps the application and infrastructure layers connected without maintaining duplicate configurations.

---

## Immutable Backend Artifact

Terraform does not build application source on EC2.

The backend image remains the SHA-tagged GHCR artifact produced during Sprint 7.

The deployment uses:

```text
ghcr.io/wondwossenh9/opsboard-backend:<git-sha>
```

The deployment philosophy remains:

```text
build once
    ↓
publish
    ↓
deploy same artifact
```

Before relying on this during automated bootstrap, unauthenticated GHCR access was tested.

After:

```text
docker logout ghcr.io
```

the SHA-tagged image could still be resolved and pulled.

This established that a fresh EC2 host would not require an interactive registry login.

---

## Database Migration During Bootstrap

The backend cannot function correctly against a database that exists but lacks its application schema.

The EC2 bootstrap therefore runs the version-controlled migration before starting the backend.

The migration uses a temporary:

```text
mysql:8.0
```

container as a client.

The database startup relationship is:

```text
RDS resource created
        ↓
EC2 bootstrap begins
        ↓
attempt migration
        ↓
retry if database not ready
        ↓
migration succeeds
        ↓
backend starts
```

The bootstrap retries migration because:

```text
RDS API says available
        ≠
every application connection is guaranteed ready at the same instant
```

If migration continues failing after the retry window, bootstrap exits instead of silently starting the application against an unprepared schema.

---

## Bootstrap Logging and Secret Hygiene

Bootstrap output is written to:

```text
/var/log/opsboard-bootstrap.log
```

The script deliberately uses:

```bash
set -euo pipefail
```

but does not enable:

```bash
set -x
```

because shell tracing could expose runtime secrets.

This established an observability tradeoff:

```text
useful bootstrap logs
        +
fail-fast behavior
        -
secret disclosure
```

Secrets should not be exposed merely to make debugging easier.

---

## IAM Bootstrap Dependency

An operational race was considered around EC2 startup and IAM readiness.

The instance needs both:

```text
Systems Manager permissions
runtime secret-read permissions
```

during bootstrap.

Explicit dependencies were therefore added so EC2 creation waits for the relevant IAM role-policy relationships.

This reduces the chance of launching the host before the permissions required by its bootstrap path are ready.

---

## First Terraform Plan

Once the main infrastructure layers were modeled, Terraform proposed:

```text
39 to add
0 to change
0 to destroy
```

This was the first complete picture of the desired environment.

The 39 count represented AWS resources being created.

IAM policy-document data sources also appeared during evaluation, but those do not represent additional AWS resources.

This distinction became visible later when:

```text
terraform state list
```

included both:

```text
data.aws_iam_policy_document...
```

and provisioned resource addresses.

---

## First Apply: Partial Failure

The first apply did not complete perfectly.

The SNS email subscription failed because the configured email input was rejected by AWS.

The important behavior was what Terraform did next.

Terraform did not automatically remove all resources that had already been created successfully.

Instead:

```text
apply begins
        ↓
many resources succeed
        ↓
SNS subscription fails
        ↓
successful resources remain
        ↓
state records successful resources
```

This demonstrated:

```text
terraform apply
        ≠
database-style transaction with full rollback
```

The failed input was corrected.

Terraform was then run again.

The second apply reported:

```text
Resources: 1 added, 0 changed, 0 destroyed.
```

Only the missing resource was created.

This was a concrete demonstration of convergence.

---

## Terraform Convergence

After the corrected apply, Terraform was run again with:

```text
terraform plan
```

It reported:

```text
No changes. Your infrastructure matches the configuration.
```

This was important evidence.

At that moment:

```text
configuration
        =
state
        =
observed AWS infrastructure
```

according to Terraform's refresh and comparison.

The successful initial deployment was therefore not treated as complete until a second plan confirmed no outstanding changes.

---

## First Application Readiness

The ALB target eventually returned:

```text
healthy
```

which demonstrated that the automated bootstrap successfully progressed far enough for:

```text
ALB
 ↓
EC2 port 80
 ↓
Nginx
 ↓
Gunicorn
 ↓
Flask /api/health
```

to work.

This proved that Terraform was not merely creating AWS objects.

It was creating an operational application path.

---

## Destroy Plan

The next stage tested whether the infrastructure was actually disposable.

Terraform produced:

```text
Plan: 0 to add, 0 to change, 39 to destroy.
```

At this stage, an important distinction appeared.

Running:

```text
terraform plan -destroy
```

does not destroy anything.

It only previews the actions.

When:

```text
terraform state list
```

was run immediately afterward, all resources were still tracked.

A normal:

```text
terraform plan
```

still reported:

```text
No changes.
```

This reinforced:

```text
plan
→ prediction

apply / destroy
→ action
```

---

## Actual Terraform Destroy

The real destroy was then executed.

Terraform followed the resource dependency graph and removed the environment.

The final result was:

```text
Destroy complete! Resources: 39 destroyed.
```

Afterward:

```text
terraform state list
```

returned no managed resources.

This represented:

```text
Terraform configuration
→ still exists

Terraform state
→ empty

AWS managed environment
→ removed
```

A new plan produced:

```text
Plan: 39 to add, 0 to change, 0 to destroy.
```

That result was a major Sprint 9 checkpoint.

Terraform had no resources left in state but still knew exactly how to reconstruct the environment.

---

## Why Destroy Was More Important Than It First Appeared

A single successful apply can hide dependencies on:

```text
manual setup
old AWS resources
shell variables
previous configuration
one-off console actions
```

The destroy test removed those hidden assumptions.

The environment was intentionally forced back to:

```text
nothing managed
```

before the second deployment.

This changed the evidence from:

```text
Terraform once created something that worked
```

to:

```text
Terraform can reconstruct the system after complete removal
```

---

## Second Clean Apply

Terraform was applied again from empty state.

AWS generated new physical resource identifiers.

The first Terraform deployment had included:

```text
VPC → vpc-0f592ca583c27082c
EC2 → i-055886e195cd03b15
```

The recreated deployment produced:

```text
VPC → vpc-080e125e9f9dcfacc
EC2 → i-02b361873b71f41ab
```

The IDs were different.

The declared architecture remained the same.

This demonstrated:

```text
physical identity
→ replaceable

desired configuration
→ durable
```

The project no longer depended on manually preserved AWS IDs.

---

## Initial ALB Failure During Recreation

During the second deployment, ALB target health initially reported:

```text
Target.FailedHealthChecks
unhealthy
```

This became an important troubleshooting exercise.

The first reaction was deliberately not:

```text
change security groups
```

or:

```text
rerun Terraform
```

or:

```text
restart everything
```

Instead, evidence was collected layer by layer.

---

## EC2 and Systems Manager Evidence

The EC2 instance reported:

```text
running
```

Systems Manager reported:

```text
Online
```

This established that:

```text
EC2 exists
        ↓
instance is running
        ↓
IAM/SSM path is functioning
```

but did not yet prove the application was ready.

The distinction was:

```text
host health
        ≠
application health
```

---

## Bootstrap Investigation

A Systems Manager command inspected:

```text
cloud-init status
bootstrap log
Docker containers
localhost /api/health
```

At that time:

```text
cloud-init status
→ running
```

The bootstrap log already showed successful progress through:

```text
host package installation
AWS CLI installation
configuration directory creation
SSM database-password retrieval
runtime environment creation
migration restoration
Nginx config restoration
Docker network creation
backend image pull
Nginx image pull
MySQL image pull
database migration
```

Most importantly:

```text
database migration succeeded
```

This ruled out several possible causes.

It established that:

```text
RDS networking
database authentication
SSM secret retrieval
database existence
schema application
```

were already working.

---

## Local HTTP Failure

The same diagnostic command attempted:

```text
curl http://127.0.0.1/api/health
```

and received:

```text
Failed to connect to 127.0.0.1 port 80
```

The bootstrap log had only reached:

```text
[opsboard] starting backend container
```

It had not yet completed:

```text
[opsboard] starting nginx container
```

Therefore the local HTTP failure was consistent with the evidence.

The system had been observed during initialization.

The correct interpretation was:

```text
port 80 unavailable
        because
Nginx not yet started
```

rather than:

```text
port 80 unavailable
        therefore
security group is broken
```

---

## Infrastructure Ready vs. Application Ready

This became one of the most valuable lessons of Sprint 9.

The second environment demonstrated:

```text
EC2 running
        ≠
application ready
```

and:

```text
SSM Online
        ≠
Nginx ready
```

and:

```text
Terraform resource creation complete
        ≠
all asynchronous initialization already finished
```

Different readiness signals answer different questions.

```text
EC2 state
→ is the VM running?

SSM PingStatus
→ can Systems Manager communicate with it?

cloud-init
→ has bootstrap completed?

Docker state
→ are runtime containers running?

localhost health
→ is the application responding locally?

ALB target health
→ can the load balancer successfully reach the application?
```

These signals should not be treated as interchangeable.

---

## Recovery Without Configuration Changes

No security-group rule was changed.

No random EC2 reboot was performed.

No Terraform resource was modified.

After bootstrap completed, ALB target health changed to:

```text
healthy
```

This proved that the initial failure was a readiness timing issue rather than a broken infrastructure definition.

The diagnostic sequence was:

```text
observe unhealthy target
        ↓
verify EC2
        ↓
verify SSM
        ↓
inspect cloud-init
        ↓
inspect bootstrap log
        ↓
confirm migration succeeded
        ↓
identify bootstrap still running
        ↓
allow initialization to finish
        ↓
ALB healthy
```

This reinforced the operating principle:

> Gather evidence before intervention.

---

## Final Terraform Convergence

After the recreated environment became healthy:

```text
terraform plan
```

again returned:

```text
No changes. Your infrastructure matches the configuration.
```

This completed the central Sprint 9 proof.

The lifecycle was:

```text
configuration
    ↓
apply
    ↓
working environment
    ↓
no changes
    ↓
destroy 39 resources
    ↓
empty state
    ↓
plan 39 resources
    ↓
apply again
    ↓
new physical AWS resources
    ↓
healthy target
    ↓
no changes
```

This is substantially stronger evidence than simply showing Terraform source files.

---

## Resource Identity vs. Desired State

Before Terraform, AWS resource IDs could feel important because they were repeatedly copied into commands.

Sprint 9 changed that perspective.

For example:

```text
old EC2
i-055886e195cd03b15
```

was destroyed.

A new EC2 appeared:

```text
i-02b361873b71f41ab
```

Likewise, the VPC identifier changed.

Nothing in the durable architecture depended on retaining the old IDs.

The lasting artifact is:

```text
Terraform configuration
```

not:

```text
a particular VPC ID
a particular subnet ID
a particular instance ID
```

This established:

```text
resource IDs
→ implementation details

Terraform relationships
→ architecture
```

---

## Terraform Destroy vs. Manual Teardown

Sprint 8 manual teardown required careful human ordering.

Terraform destroy used the dependency graph already encoded in configuration and state.

The contrast was:

```text
Manual teardown
→ operator reasons about dependency order

Terraform destroy
→ dependency graph determines order
```

Manual understanding was still valuable because it made Terraform's behavior understandable rather than magical.

But once encoded correctly, repeated teardown no longer required manually reconstructing the dependency tree.

---

## Source of Truth

By the end of the sprint:

```text
network topology
security relationships
IAM relationships
compute configuration
database configuration
load balancing
monitoring
alerting
runtime secret path
application bootstrap
```

were all represented in repository-controlled configuration.

This changed the operational model from:

```text
remember how the environment was created
```

to:

```text
read and apply the configuration
```

That is one of the most important practical benefits of Infrastructure as Code.

---

## Current Limitations

Sprint 9 improved reproducibility, but the environment is intentionally not presented as production-complete.

Current limitations include:

```text
local Terraform state
no shared remote-state locking
single EC2 application instance
EC2 in a public subnet
Single-AZ RDS
HTTP rather than HTTPS
no Auto Scaling Group
no WAF
no centralized application logging
user-data based configuration
mutable supporting image tags
human SNS email confirmation
no automated alert-email validation yet
```

These limitations define future engineering work.

They do not invalidate the Sprint 9 objective, which was reproducible infrastructure rather than complete production hardening.

---

## Cost Awareness

The destroy/recreate experiment also reinforced the cost model.

Resources such as:

```text
Application Load Balancer
RDS
EC2
public IPv4
storage
```

can continue generating charges while the environment remains active.

Terraform now provides a cleaner lab lifecycle:

```text
terraform apply
        ↓
learn / test / demonstrate
        ↓
document evidence
        ↓
terraform destroy
```

This is easier to repeat safely than manually locating and deleting many individual resources.

Cost remains an operational concern alongside security and reliability.

---

## Key Engineering Lessons

* Infrastructure as Code is stronger when it follows manual understanding rather than replacing understanding.
* Terraform configuration, Terraform state, and real infrastructure are different concepts.
* An AWS resource existing does not mean Terraform manages it.
* Terraform does not automatically adopt matching manually created resources.
* Resource references encode architecture and build the dependency graph.
* AWS-generated identifiers should not become durable application configuration.
* Terraform can retain successfully created resources after a partial apply failure.
* A second apply can converge on the missing desired state.
* `terraform plan` is a prediction, not an execution.
* `terraform destroy` is required to actually remove managed resources.
* A clean empty state followed by `39 to add` is strong reproducibility evidence.
* A second apply creating different AWS IDs proves that physical resource identity is replaceable.
* Sensitive values require more than display redaction when state exposure matters.
* Ephemeral variables and write-only provider arguments improve secret handling.
* Runtime secrets can be delivered through SSM instead of embedded directly in EC2 user data.
* Existing repository-owned migration and Nginx configuration should be reused rather than duplicated.
* Terraform should create a usable application environment when reproducibility is the goal, not merely empty infrastructure.
* EC2 `running` is not equivalent to application readiness.
* Systems Manager `Online` is not equivalent to Nginx or backend readiness.
* Cloud-init, Docker state, local health checks, and ALB target health provide different operational signals.
* A temporarily unhealthy load-balancer target does not automatically imply a networking or security-group problem.
* Evidence should be gathered before infrastructure is modified.
* Destroy and recreation testing can expose hidden manual dependencies that a single successful deployment may not reveal.
* Terraform makes repeated cost-conscious lab creation and removal practical.

---

## Sprint 9 Outcome

Sprint 8 produced:

```text
manually understood AWS infrastructure
```

Sprint 9 converted that understanding into:

```text
declarative
version-controlled
dependency-aware
destroyable
recreatable
Terraform-managed infrastructure
```

The strongest Sprint 9 evidence was:

```text
terraform apply
        ↓
working environment
        ↓
terraform plan
        ↓
no changes
        ↓
terraform destroy
        ↓
39 resources destroyed
        ↓
terraform state list
        ↓
empty
        ↓
terraform plan
        ↓
39 to add
        ↓
terraform apply
        ↓
new VPC
new EC2
new supporting resources
        ↓
ALB target healthy
        ↓
terraform plan
        ↓
no changes
```

The project therefore no longer depends on one particular set of AWS resource identifiers or a remembered sequence of console operations.

The desired AWS environment is now encoded as infrastructure configuration.

Sprint 8 established:

```text
understanding
```

Sprint 9 established:

```text
reproducibility
```

---

# Sprint 10 — Remote Terraform State & Workflow Hardening

## Sprint Objective

Sprint 9 established that OpsBoard could be created, destroyed, and recreated from Terraform.

Sprint 10 focused on the operational layer surrounding Terraform itself:

```text
Where does state live?
How is it protected?
How are concurrent operations controlled?
How can an older state be recovered?
How should Terraform changes be validated before merge?
```

The objective was to move from workstation-local Terraform state toward a safer, collaboration-ready workflow.

---

## Local State Limitation

Before Sprint 10, the main Terraform state lived on the development workstation.

This worked for the Sprint 9 learning environment, but introduced several risks:

```text
single-machine dependency
multiple engineers could hold different state copies
no shared lock
limited recovery history
state should not be committed to Git
```

The desired model became:

```text
Developer / CI
      ↓
Amazon S3
├── state
├── version history
└── lock file
      ↓
AWS
```

---

## Terraform Bootstrap Problem

A remote backend introduces a dependency problem.

Terraform needs the backend bucket before it can initialize the configuration that would create the bucket.

Conceptually:

```text
bucket required
    ↓
terraform init
    ↓
terraform apply
    ↓
bucket created
```

This cycle was broken by creating a separate Terraform root:

```text
infrastructure/
├── terraform-bootstrap/
└── terraform/
```

The bootstrap root owns the state-storage infrastructure.

The application root uses that infrastructure.

This reinforced:

```text
one repository
        ≠
one Terraform state
```

---

## Bootstrap Infrastructure

The bootstrap root manages:

```text
aws_s3_bucket
aws_s3_bucket_public_access_block
aws_s3_bucket_versioning
aws_s3_bucket_server_side_encryption_configuration
```

The first plan produced:

```text
Plan: 4 to add, 0 to change, 0 to destroy.
```

The bucket was configured with:

```text
public access blocked
versioning enabled
AES256 server-side encryption
force_destroy = false
prevent_destroy = true
```

---

## Destroy Protection Test

The bootstrap root was deliberately tested with:

```bash
terraform plan -destroy
```

Terraform showed the proposed four-resource destruction but then rejected the operation because the bucket uses:

```text
lifecycle.prevent_destroy
```

The result was:

```text
Error: Instance cannot be destroyed
```

This demonstrated the difference between:

```text
force_destroy = false
```

and:

```text
prevent_destroy = true
```

`prevent_destroy` is a Terraform lifecycle guardrail.

`force_destroy = false` prevents Terraform from automatically deleting bucket contents in order to remove the bucket.

---

## Main State Before Migration

The Sprint 9 AWS stack had already been destroyed.

The main local state therefore contained:

```text
Resources: 0
```

but still had Terraform metadata including lineage and serial history.

A manual backup was retained before changing backend configuration.

The important distinction was:

```text
empty state
        ≠
no state metadata
```

---

## S3 Backend Configuration

The application Terraform root was updated with:

```hcl
backend "s3" {
  key          = "opsboard/prod/terraform.tfstate"
  region       = "us-east-1"
  encrypt      = true
  use_lockfile = true
}
```

The bucket name was supplied during initialization rather than committed directly into the configuration.

---

## Migration Verification Problem

After backend initialization, the first verification showed:

```text
Serial: 0
Lineage:
Resources: 0
```

and a direct S3 object lookup returned:

```text
404 Not Found
```

This was an important finding.

A command appearing to complete successfully did not automatically prove that the expected state object had been persisted.

The migration was therefore investigated rather than assumed to be correct.

---

## Remote State Baseline

After recovery of the remote-state baseline, S3 contained the application state object.

The new remote state had its own lineage and tracked:

```text
Resources: 0
```

The original Sprint 9 local backup also tracked:

```text
Resources: 0
```

Independent AWS checks confirmed that the application stack was absent.

Therefore there was no Terraform resource ownership to recover from the old lineage.

The decision was made not to force the historical lineage into the new remote state.

The final relationship was:

```text
Terraform configuration → 39 desired resources
remote state            → 0 managed resources
AWS application stack   → absent
```

Terraform correctly reported:

```text
Plan: 39 to add, 0 to change, 0 to destroy.
```

---

## S3 Native Locking

The S3 backend uses:

```hcl
use_lockfile = true
```

No DynamoDB locking table was introduced.

Terraform logging showed:

```text
Attempting to lock remote state
Locked remote state
Unlocked remote state
```

S3 version history also showed historical `.tflock` versions and delete markers.

This proved that normal Terraform operations created and removed the native S3 lock file.

---

## First Lock Experiment

An initial attempt used:

```text
terraform console
```

as the intended lock holder.

A second Terraform plan still succeeded.

No active `.tflock` object was observed.

The experiment was therefore rejected as evidence.

This was an important methodological lesson:

```text
expected behavior
        ≠
observed behavior
```

A test only counts when the evidence supports the conclusion.

---

## Deterministic Lock Contention Test

A second experiment used a normal Terraform plan with logging enabled.

The process was allowed to reach:

```text
Locked remote state
```

and was then paused with a Unix process signal.

The process remained alive while retaining the state lock.

A second terminal then ran:

```bash
terraform plan -lock-timeout=5s
```

Terraform returned:

```text
Error acquiring the state lock
```

with S3 reporting:

```text
412 PreconditionFailed
```

The second process also displayed lock ownership metadata.

The first process was resumed and completed normally.

Terraform released the lock.

A later plan from the second terminal then succeeded.

This established:

```text
writer A owns lock
        ↓
writer B blocked
        ↓
writer A completes
        ↓
lock released
        ↓
writer B succeeds
```

S3-native state locking was therefore proven experimentally.

---

## State Version Inspection

When S3 object versions were first listed with the prefix:

```text
opsboard/prod/terraform.tfstate
```

the result included both:

```text
terraform.tfstate
terraform.tfstate.tflock
```

because both keys share the same prefix.

This initially made the output appear to contain many application state versions.

The query was corrected to filter by exact object key.

The lesson was:

```text
prefix match
        ≠
exact object match
```

Operational evidence must be interpreted, not merely collected.

---

## Recovery Lab Design

The real application state was deliberately not used for the recovery experiment.

A separate key was created:

```text
opsboard/labs/recovery.tfstate
```

The lab used:

```text
terraform_data
```

instead of AWS infrastructure.

This allowed state behavior to be tested without creating billable resources or risking the real application state.

---

## Recovery Version 1

The initial lab configuration contained:

```text
input = "version-1"
```

After apply, the state showed:

```text
Serial: 1
Input: version-1
```

---

## Recovery Version 2

The configuration was changed to:

```text
input = "version-2"
```

A second apply produced a new S3 object version.

The new state showed:

```text
Serial: 2
Input: version-2
```

Both states retained the same Terraform lineage.

This reinforced:

```text
lineage
→ identity of the logical Terraform state

serial
→ generation within that state
```

---

## Historical State Restoration

The older S3 object version was restored as the newest S3 object.

This created a new:

```text
S3 VersionId
```

whose contents still represented:

```text
Terraform Serial: 1
Input: version-1
```

This demonstrated that:

```text
S3 object version
        ≠
Terraform state serial
```

The configuration still requested:

```text
version-2
```

Terraform plan therefore reported:

```text
version-1 → version-2
```

with:

```text
Plan: 0 to add, 1 to change, 0 to destroy.
```

This was direct evidence that the historical state had actually been restored.

---

## Recovery to Desired State

Terraform apply was run normally.

The state returned to:

```text
version-2
```

A final plan reported:

```text
No changes. Your infrastructure matches the configuration.
```

S3 contained multiple historical state versions representing the full experiment.

The tested lifecycle was:

```text
version-1
    ↓
version-2
    ↓
restore version-1
    ↓
Terraform detects difference
    ↓
apply desired version-2
    ↓
No changes
```

---

## Terraform CI

A dedicated workflow was added:

```text
.github/workflows/terraform.yml
```

A matrix validates both roots:

```text
infrastructure/terraform
infrastructure/terraform-bootstrap
```

Each job performs:

```text
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate -no-color
```

The use of:

```text
-backend=false
```

means CI validation does not require:

```text
AWS credentials
S3 state access
Terraform state locking
AWS infrastructure access
```

This separates:

```text
configuration validation
```

from:

```text
infrastructure planning or deployment
```

---

## Required Check Trigger Design

After the Terraform matrix checks were added to branch protection, the workflow trigger design was reconsidered.

The workflow originally used path filters.

A required workflow skipped by path filtering can leave required checks without a successful result.

The path filters were therefore removed.

Terraform CI now runs on every pull request targeting `main`.

This established another lesson:

```text
workflow trigger design
        +
branch protection design
        =
one combined control
```

A workflow cannot be evaluated only in isolation once its checks become required merge gates.

---

## Pull Request Verification

Pull Request #16 ran:

```text
backend-ci
integration-tests
terraform-ci (infrastructure/terraform)
terraform-ci (infrastructure/terraform-bootstrap)
```

All required checks passed.

The image publication job remained skipped on the pull request, as designed.

---

## Post-Merge Verification

Pull Request #16 was merged into `main`.

Merge commit:

```text
808abfd8cc91190079fec75ed23ac08bf14d3d6f
```

The push to `main` triggered both application and Terraform CI.

Results:

```text
backend-ci                                      → success
integration-tests                               → success
publish-image                                   → success
terraform-ci (infrastructure/terraform)         → success
terraform-ci (infrastructure/terraform-bootstrap) → success
```

This verified that the workflows remained healthy after integration.

---

## AWS Authentication Expiry

Several Terraform operations were interrupted because the AWS CLI login session expired.

Terraform reported:

```text
No valid credential sources found
login session has expired
```

Reauthentication with:

```bash
aws login --remote
```

restored access.

The important distinction was:

```text
AWS authentication session expired
        ≠
AWS resources deleted
        ≠
S3 state deleted
```

Authentication controls client access.

It does not determine the lifecycle of already-existing durable infrastructure.

---

## Final Application-State Verification

After merging the backend configuration, the local Terraform working directory was reinitialized against the existing S3 backend.

A final plan returned:

```text
Plan: 39 to add, 0 to change, 0 to destroy.
```

This remained the correct outcome:

```text
configuration → 39 resources
remote state  → 0 resources
AWS stack     → absent
```

No apply was performed.

The application environment remains intentionally destroyed for cost control.

---

## Sprint 10 Lessons

- Terraform state should be treated as operational data, not normal source code.
- A repository can contain multiple Terraform roots with independent ownership and state.
- Backend infrastructure introduces a bootstrap problem that must be solved deliberately.
- S3 public-access blocking and encryption should be explicitly modeled.
- Versioning provides recoverable state history.
- `prevent_destroy` and `force_destroy` protect against different failure modes.
- Successful `terraform init` is not sufficient evidence that the expected remote state exists.
- State verification should use both Terraform and backend-side evidence.
- Native S3 `.tflock` locking can prevent concurrent Terraform writers.
- A failed lock attempt should be investigated before considering `force-unlock`.
- A test that does not produce the expected evidence should not be counted as successful.
- S3 prefix searches can mix state and lock objects.
- S3 VersionIds and Terraform state serials are different concepts.
- Recovery testing should use an isolated state whenever possible.
- `terraform init -backend=false` allows safe Terraform CI validation without AWS credentials.
- Required status checks must be designed together with workflow triggers.
- AWS authentication-session expiry does not destroy infrastructure or state.
- An empty state can still contain lineage and serial metadata.
- Evidence-driven troubleshooting is more reliable than assumptions about how a tool should behave.

---

## Sprint 10 Outcome

Sprint 8 established:

```text
manual AWS understanding
```

Sprint 9 established:

```text
Terraform reproducibility
```

Sprint 10 established:

```text
remote application state
        ↓
state protection
        ↓
state locking
        ↓
state recovery
        ↓
Terraform CI
        ↓
required infrastructure merge gates
```

OpsBoard now demonstrates both Terraform infrastructure provisioning and safer Terraform state operations.

The next major operations focus is:

```text
centralized application logging
```

followed by:

```text
HTTPS / TLS
high availability
Kubernetes
production hardening
```