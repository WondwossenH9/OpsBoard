# Changelog

All notable changes to OpsBoard are documented in this file.

## v0.7.0 — AWS Deployment & Observability

### Added

- Dedicated AWS VPC using `10.0.0.0/16`.
- Two public subnets across separate Availability Zones.
- Two private database subnets across separate Availability Zones.
- Internet Gateway and public route table.
- Dedicated private database route table with no Internet default route.
- Security groups separating ALB, EC2, and RDS traffic.
- EC2 `t3.micro` Docker application host.
- AWS Systems Manager Session Manager administration without inbound SSH.
- Private Amazon RDS MySQL 8.0 database.
- RDS subnet group spanning two Availability Zones.
- Internet-facing Application Load Balancer.
- ALB target group using `/api/health`.
- Native CloudWatch monitoring for ALB, EC2, and RDS.
- CloudWatch alarms for:
  - unhealthy ALB targets;
  - EC2 status-check failures;
  - low RDS free storage.
- Amazon SNS email notification topic for application availability alarms.
- AWS Budget for cost monitoring.
- Detailed AWS deployment documentation in `docs/aws-deployment.md`.

### Deployment

- Deployed the existing SHA-tagged backend image from GitHub Container Registry rather than rebuilding application source on EC2.
- Preserved the Sprint 7 immutable-artifact principle:

```text
Build once
    ↓
publish artifact
    ↓
configure at runtime
    ↓
deploy the same artifact
```

- Ran Nginx and the Gunicorn backend as Docker containers on EC2.
- Published Gunicorn only on the EC2 loopback interface.
- Exposed public HTTP traffic through Nginx on port `80`.
- Applied the existing version-controlled SQL migration to Amazon RDS.
- Verified RDS DNS resolution, TCP connectivity, authentication, database existence, schema creation, and application queries independently.
- Verified public application access through the ALB:

```text
GET /api/health    → 200 OK
GET /api/incidents → 200 OK
```

### Security

- Allowed public HTTP traffic only to the Application Load Balancer.
- Restricted EC2 HTTP ingress to the ALB security group.
- Restricted RDS MySQL ingress to the EC2 security group.
- Kept RDS publicly inaccessible.
- Did not expose Gunicorn port `8000` publicly.
- Did not open inbound SSH port `22`.
- Used Systems Manager Session Manager for EC2 administration.
- Verified that direct HTTP access to the EC2 public IPv4 address timed out while ALB traffic continued to succeed.
- Kept runtime database credentials outside the Git repository.

### Observability

- Observed ALB metrics including:
  - `HealthyHostCount`
  - `UnHealthyHostCount`
  - `RequestCount`
  - target HTTP status counts
  - ALB `502` and `503` counts
  - `TargetConnectionErrorCount`
  - `TargetResponseTime`
- Observed EC2:
  - `CPUUtilization`
  - `CPUCreditBalance`
  - instance status checks
  - system status checks
- Observed RDS:
  - `DatabaseConnections`
  - `CPUUtilization`
  - `FreeableMemory`
  - `FreeStorageSpace`
  - CPU credit metrics
  - surplus-credit metrics
  - `SwapUsage`
- Verified that a deliberately long-lived MySQL connection became visible through the RDS `DatabaseConnections` metric.
- Verified that CPU credits rebuilt after the RDS instance restarted.
- Verified that temporary RDS surplus CPU credits were repaid with `CPUSurplusCreditsCharged = 0`.

### Failure Testing

- Deliberately stopped the Nginx container while leaving the backend and database running.
- Verified the ALB target became unhealthy.
- Correlated the failure with:

```text
TargetConnectionErrorCount ↑
HTTPCode_ELB_502_Count      ↑
```

- Verified that a longer period without a usable backend produced ALB-generated HTTP `503` responses.
- Restarted only the failed Nginx layer rather than restarting the complete stack.
- Verified recovery progressively:

```text
Nginx running
    ↓
EC2-local /api/health → 200
    ↓
ALB target → healthy
    ↓
public API → 200
```

### Alerting

- Created the `opsboard-alb-unhealthy-target` CloudWatch alarm.
- Configured two consecutive one-minute unhealthy datapoints before entering `ALARM`.
- Deliberately triggered the alarm by stopping Nginx.
- Verified the alarm transitioned:

```text
OK
→ ALARM
→ OK
```

- Created an SNS topic for OpsBoard alerts.
- Confirmed the email subscription.
- Verified SNS independently with a test notification.
- Configured both CloudWatch `ALARM` and `OK` actions.
- Verified CloudWatch alarm history recorded successful SNS actions for both failure and recovery.
- Verified SNS metrics showed successful notification delivery and zero notification failures.

### Cost Management

- Created a monthly AWS Budget.
- Avoided a NAT Gateway for the learning deployment.
- Used small burstable EC2 and RDS instance classes.
- Used Single-AZ RDS for the lab environment.
- Used native AWS metrics before introducing additional monitoring agents.
- Monitored CPU-credit behavior for both cost and performance awareness.
- Established a lab operating pattern of stopping or deleting billable infrastructure when it is not required.
- Identified the Application Load Balancer as a resource that must be deleted, rather than stopped, to end its hourly charges.

### Lessons

- A public subnet and public IPv4 address do not automatically make a service reachable; routing and security rules both matter.
- Security-group references provide stronger tier isolation than broad VPC CIDR rules.
- Infrastructure should be diagnosed layer by layer rather than by changing security rules at random.
- Database networking, authentication, schema state, and application queries are separate failure domains.
- An ALB `502` and an ALB `503` represent different failure conditions.
- Application failure can occur while EC2 infrastructure status checks remain healthy.
- Monitoring data can lag behind the event being observed.
- Metrics, health checks, logs, and alarms answer different operational questions.
- An alarm configuration should be deliberately triggered and recovered rather than assumed to work.
- Notification delivery should be verified independently from alarm state.
- Internet-facing infrastructure receives unsolicited traffic even when its endpoint has not been intentionally advertised.
- Cost is an operational concern and should be monitored alongside reliability and performance.
- Manual infrastructure understanding should precede Infrastructure as Code when the learning objective is to understand the underlying AWS resources.

### Verified

- EC2 application host reachable through Systems Manager.
- No inbound SSH access required.
- RDS inaccessible directly from the Internet.
- EC2 direct public HTTP blocked.
- ALB public HTTP path returns `200 OK`.
- Nginx successfully proxies to Gunicorn.
- Gunicorn successfully serves Flask.
- Flask successfully queries private RDS MySQL.
- ALB health checks detect application-layer failures.
- CloudWatch captures unhealthy-target transitions.
- CloudWatch distinguishes connection-related `502` failures from no-healthy-target `503` failures.
- EC2 infrastructure status checks remain healthy during an application-only Nginx failure.
- CloudWatch alarm transitions correctly between `OK` and `ALARM`.
- SNS successfully receives CloudWatch alarm actions.
- SNS notification delivery succeeds with zero reported failures.
- Application recovery returns the ALB target and CloudWatch alarm to healthy state.

### Sprint Outcome

OpsBoard progressed from a CI-controlled container release into an AWS-hosted, monitored, and alerting application platform.

The deployed path is now:

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

with operations supported by:

```text
CloudWatch metrics
    ↓
CloudWatch alarms
    ↓
Amazon SNS
    ↓
email notification
```

Sprint 8 establishes the manually understood architecture that Sprint 9 will reproduce using Terraform.

---

---
## v0.6.0 — CI/CD & Release Engineering

### Added

- GitHub Actions CI for pushes and pull requests targeting `main`.
- Python syntax validation using `compileall`.
- Automated backend unit tests.
- Real MySQL 8.0 integration testing in GitHub Actions.
- Docker image build validation in CI.
- Protected `main` branch with required CI status checks.
- Gated backend image publishing to GitHub Container Registry.
- Git commit SHA and `latest` image tags.
- Release-specific Docker Compose configuration using published GHCR artifacts.
- Version-controlled database migration for the `incidents` table.
- One-shot database migration service with dependency gating.
- Gunicorn production WSGI server with two workers.

### Improved

- Pull requests are validated before merge without publishing release artifacts.
- Backend container images are published only after required checks pass on `main`.
- Release environments consume tested container artifacts instead of rebuilding backend source.
- MySQL readiness checks now verify TCP connectivity required by dependent containers.
- Backend startup waits for successful database migration.
- Backend container runtime changed from Flask's development server to Gunicorn.
- Gunicorn access and error logs are written to container stdout/stderr.
- Single-incident database access now uses consistent context-managed resource handling.

### Testing

- Added 5 backend unit tests covering:
  - Health endpoint availability.
  - Health response contract.
  - Incident collection retrieval with a mocked database.
  - Collection endpoint database failure handling.
  - Single-incident database failure handling.
- Added 3 integration tests using real MySQL covering:
  - Incident collection retrieval.
  - Existing incident retrieval.
  - Missing incident `404` behavior.
- Deliberately introduced and corrected a CI syntax failure to verify pipeline failure behavior.
- Verified database-failure `503` behavior under Gunicorn.
- Verified the published GHCR image could be pulled and executed outside the CI runner.

### Release Engineering

- Established the release flow:

```text
Feature Branch
    ↓
Pull Request
    ↓
backend-ci + integration-tests
    ↓
Protected main
    ↓
Release gate
    ↓
Build backend image
    ↓
Publish to GHCR
    ↓
SHA-tagged release artifact
```

- Verified a published backend image using its Git commit SHA tag.
- Verified runtime configuration without rebuilding the container image.
- Added an isolated `opsboard-release` Compose environment.
- Verified fresh-environment deployment using a new MySQL volume.
- Verified database migration completes before backend startup.
- Verified the final release stack through Nginx:

```text
GET /api/health    → 200 OK
GET /api/incidents → 200 OK
```

### Operational Hardening

- Replaced Flask's development server with Gunicorn.
- Verified two Gunicorn workers start successfully.
- Removed Flask debugger/reloader behavior from the release runtime.
- Preserved centralized `503 Service Unavailable` handling under Gunicorn.
- Improved MySQL health checks to validate TCP readiness.

### Lessons

- CI should be tested in both failure and success states.
- Required status checks turn CI from advisory feedback into an enforcement mechanism.
- Unit tests and integration tests validate different layers of the system.
- Release artifacts should be traceable to source commits.
- Deployment environments should consume tested artifacts rather than rebuild source.
- Database schema must be version-controlled and reproducible.
- Migration jobs should block application startup when schema preparation fails.
- Health checks should validate the capability required by dependent services.
- Production containers should run production application servers rather than development servers.

### Verified

- Pull-request CI blocks unsafe changes from reaching `main`.
- Release image publication occurs only after both CI jobs succeed.
- SHA-tagged backend images can be pulled successfully from GHCR.
- The same published artifact works with runtime-supplied configuration.
- Fresh release environments create the required database schema automatically.
- Migration failure prevents backend startup.
- Successful migration exits with code `0`.
- Gunicorn serves the Flask application on port `8000`.
- Nginx successfully proxies requests to the Gunicorn backend.
- Fresh release deployment returns `200 OK` for both health and incident endpoints.

---
## v0.5.0 — Operational Robustness

### Added

- Centralized MySQL database exception handling.
- Safe JSON responses for database failures.
- Server-side logging for database errors.
- Database resource management using Python context managers.

### Improved

- Refactored both incident endpoints to use consistent database resource management.
- Database failures now return HTTP `503 Service Unavailable` instead of exposing internal server errors.
- Client-facing database error messages no longer expose connector or infrastructure details.
- Database errors are logged server-side for diagnostics.

### Verified

- Existing incident returns `200 OK`.
- Missing incident returns `404 Not Found`.
- Database outage returns `503 Service Unavailable`.
- API successfully recovers to `200 OK` after MySQL becomes healthy again.
- `/api/incidents` and `/api/incidents/<id>` both return `503 Service Unavailable` when MySQL is unavailable.

---

## v0.4.0 — Database Integration & Multi-Service Architecture

### Added

- MySQL 8.0 database service.
- Persistent Docker named volume for MySQL data.
- MySQL `incidents` table.
- MySQL Connector/Python dependency.
- Database-backed incident retrieval.
- Environment-based database configuration.
- `.env.example` configuration template.
- Root `.gitignore` for protecting environment files and development artifacts.
- MySQL health check using `mysqladmin ping`.
- Docker Compose dependency condition using `service_healthy`.

### Improved

- Replaced the temporary in-memory incident data with MySQL persistence.
- Flask now retrieves incident data from MySQL.
- Flask connects to MySQL using the Docker Compose service name `mysql`.
- Database credentials are supplied through environment variables rather than being hardcoded in `compose.yaml`.
- Docker Compose waits for MySQL to pass its health check before starting the backend container.
- Only Nginx is exposed to the host.
- Backend port `8000` remains internal to the Docker network.
- MySQL port `3306` remains internal to the Docker network.

### Architecture

The request path is now:

Browser → Nginx → Flask → MySQL

Docker Compose provides:

- Internal service networking.
- DNS-based service discovery.
- Container-to-container communication.
- Persistent storage through a named volume.
- Service health checks.

### Verified

- Verified MySQL database initialization.
- Verified MySQL user authentication.
- Verified `incidents` table creation.
- Verified incident insertion and retrieval.
- Verified backend-to-MySQL TCP connectivity.
- Verified Docker Compose DNS resolution using `mysql`.
- Verified MySQL health status.
- Verified Nginx reverse proxying.
- Verified `GET /api/incidents`.
- Verified `GET /api/incidents/<id>`.
- Verified `404 Not Found` for nonexistent incidents.
- Verified complete Nginx → Flask → MySQL request flow.
- Verified database persistence through the Docker named volume.

### Security

- Added `.env` to `.gitignore`.
- Added `.env.example` without real credentials.
- Removed hardcoded database credentials from `compose.yaml`.
- Kept backend and MySQL ports unpublished to the host.
- Kept database access restricted to the internal Docker network.

### Lessons

- Containers are ephemeral, but persistent data should live outside the container filesystem.
- A started container does not necessarily mean the application inside it is ready.
- `service_healthy` is more appropriate than `service_started` when a dependent service requires actual application readiness.
- Docker Compose service names should be used instead of hardcoded container IP addresses.
- Environment variables provide a cleaner separation between application configuration and source code.
- Named volumes provide persistence across container recreation.

---

## v0.3.0 — Reverse Proxy Architecture

### Added

- Docker Compose orchestration.
- Nginx reverse proxy.
- Custom Nginx configuration.
- Automatic Docker networking.
- Internal service discovery using Docker Compose DNS.
- Multi-container application architecture.

### Improved

- Browser traffic now flows through Nginx instead of directly to the Flask application.
- Backend service is no longer exposed directly to the host.
- Project documentation updated to reflect the reverse proxy architecture.

### Learned

- Docker Compose orchestration.
- Reverse proxy architecture.
- Internal Docker networking.
- Docker Compose service discovery.
- Difference between `depends_on` and request routing through `proxy_pass`.

---

## v0.2.0 — Containerized Backend

### Added

- Dockerfile for the Flask backend.
- Optimized Docker layer caching.
- `.dockerignore`.
- Containerized Flask API.

### Improved

- Used `python:3.12-slim` as the backend base image.
- Structured Dockerfile layers to improve build-cache reuse.
- Added container port documentation using `EXPOSE 8000`.

### Learned

- Docker images and layers.
- Docker build context.
- Layer caching.
- `.dockerignore`.
- Container lifecycle.
- Port publishing and container networking.

---

## v0.1.0 — Flask API Foundation

### Added

- Initial Flask REST API.
- Root endpoint.
- Health check endpoint.
- Incident listing endpoint.
- Individual incident retrieval endpoint.
- JSON API responses.
- Initial project structure.
- Initial project documentation.

### Learned

- Flask application structure.
- REST API fundamentals.
- JSON responses using `jsonify()`.
- HTTP status codes.
- Handling missing resources with `404 Not Found`.
- Basic API routing.
