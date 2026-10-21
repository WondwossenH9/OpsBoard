# Changelog

All notable changes to OpsBoard are documented in this file.

## v0.8.0 — Terraform Infrastructure as Code

### Added

- Terraform infrastructure configuration under `infrastructure/terraform/`.
- Terraform `1.16.x` compatibility requirements.
- HashiCorp AWS Provider `6.69.x`.
- Provider dependency locking through `.terraform.lock.hcl`.
- Terraform-managed AWS networking:
  - dedicated VPC using `10.0.0.0/16`;
  - two public subnets across separate Availability Zones;
  - two private database subnets across separate Availability Zones;
  - Internet Gateway;
  - public route table;
  - private database route table;
  - subnet route-table associations.
- Terraform-managed security groups for:
  - Application Load Balancer;
  - EC2 application host;
  - Amazon RDS.
- Standalone Terraform security-group rule resources for:
  - public HTTP to the ALB;
  - ALB HTTP to EC2;
  - EC2 MySQL access to RDS;
  - outbound traffic.
- Terraform-managed IAM resources:
  - EC2 trust policy;
  - `OpsBoardEC2Role`;
  - `AmazonSSMManagedInstanceCore` attachment;
  - EC2 instance profile;
  - least-privilege runtime secret policy.
- Terraform-managed EC2 application host.
- Terraform-managed private Amazon RDS MySQL database.
- Terraform-managed RDS subnet group.
- Terraform-managed Application Load Balancer.
- Terraform-managed target group and health check.
- Terraform-managed ALB listener and EC2 target attachment.
- Terraform-managed CloudWatch alarms.
- Terraform-managed Amazon SNS alert topic and email subscription.
- Terraform-managed SSM Parameter Store database secret.
- EC2 user-data bootstrap template.
- Terraform variable example file.
- Dedicated Terraform deployment documentation in `docs/terraform-deployment.md`.

### Infrastructure as Code

Converted the AWS architecture manually established in Sprint 8 into Terraform configuration.

The infrastructure lifecycle is now driven by:

```text
Terraform configuration
        ↓
dependency graph
        ↓
AWS resources
```

AWS-generated resource IDs are referenced through Terraform relationships rather than manually copied between resources.

Examples include:

```text
VPC
 ↓
subnets
 ↓
route tables
 ↓
security groups
 ↓
EC2 / RDS / ALB
```

Terraform also passes generated infrastructure values such as the RDS endpoint into the EC2 application bootstrap automatically.

### Network Architecture

Terraform reproduces the Sprint 8 network design:

```text
Internet
    ↓
Application Load Balancer
    ↓
EC2
    ↓
Amazon RDS MySQL
```

The VPC uses:

```text
10.0.0.0/16
```

with:

```text
Public A      10.0.1.0/24
Public B      10.0.2.0/24
Private DB A  10.0.11.0/24
Private DB B  10.0.12.0/24
```

The database subnets have no Internet default route.

No NAT Gateway is used in the current cost-conscious learning environment.

### Security

Preserved the Sprint 8 tiered security model:

```text
Internet
    ↓ TCP 80
ALB Security Group
    ↓ TCP 80
EC2 Security Group
    ↓ TCP 3306
RDS Security Group
```

The application host does not expose inbound SSH.

Administrative access remains available through AWS Systems Manager.

EC2 uses IMDSv2 with metadata tokens required.

The root EBS volume is encrypted.

RDS storage is encrypted and the database remains publicly inaccessible.

### Secret Management

Introduced Terraform secret handling that avoids embedding the database password directly in EC2 user data.

The password flow is:

```text
local Terraform variable
        ↓
ephemeral sensitive value
        ├────────→ RDS write-only password
        |
        └────────→ SSM SecureString write-only value
                          ↓
                    EC2 IAM role
                          ↓
                    ssm:GetParameter
                          ↓
                runtime environment file
```

The database-password Terraform variable is:

```text
sensitive
ephemeral
```

RDS and SSM Parameter Store use write-only provider arguments.

The real `terraform.tfvars` file is excluded from Git.

The repository contains only:

```text
terraform.tfvars.example
```

with placeholder values.

### Automated EC2 Bootstrap

Added `user-data.sh.tftpl` so a newly created EC2 instance can configure the OpsBoard runtime without manual SSH or Session Manager installation steps.

The bootstrap automatically:

```text
installs Docker
        ↓
installs AWS CLI if required
        ↓
creates protected configuration storage
        ↓
retrieves DB password from SSM
        ↓
creates backend runtime environment
        ↓
restores SQL migration
        ↓
restores Nginx configuration
        ↓
creates Docker network
        ↓
pulls immutable backend image
        ↓
pulls Nginx and MySQL client images
        ↓
applies database migration
        ↓
starts backend
        ↓
starts Nginx
        ↓
checks local application health
```

Bootstrap output is recorded in:

```text
/var/log/opsboard-bootstrap.log
```

Shell tracing is deliberately disabled to avoid leaking runtime secrets into logs.

### Immutable Deployment Artifact

The Terraform deployment reuses the existing Sprint 7 backend artifact rather than rebuilding application source on EC2.

The backend is deployed using its immutable Git commit SHA tag:

```text
ghcr.io/wondwossenh9/opsboard-backend:<git-commit-sha>
```

Unauthenticated registry access to the release artifact was verified before relying on it during fresh EC2 bootstrap.

This preserves:

```text
Build once
    ↓
publish
    ↓
deploy the same artifact
```

### Database Migration

The existing repository migration:

```text
db/migrations/001_create_incidents.sql
```

is reused by the Terraform bootstrap.

Terraform reads the version-controlled migration and supplies it to EC2 rather than maintaining a second infrastructure-specific schema definition.

The bootstrap retries migration because RDS resource creation does not guarantee immediate application readiness.

A successful migration is required before the backend starts.

### Configuration Reuse

Terraform also reuses the existing:

```text
nginx/nginx.conf
```

configuration.

The migration and Nginx configuration are passed through the user-data template from their repository-owned source files.

This avoids maintaining duplicate deployment configuration.

### Monitoring and Alerting

Terraform now manages the Sprint 8 monitoring resources:

```text
ALB unhealthy target alarm
EC2 status-check failure alarm
RDS low-storage alarm
SNS alert topic
SNS email subscription
```

The ALB unhealthy-target alarm publishes both failure and recovery transitions to SNS.

The email address remains a local Terraform input rather than a hardcoded repository value.

### Partial Apply Recovery

The first Terraform apply encountered an SNS subscription error because the supplied email value was rejected by AWS.

Terraform had already created the other successful resources.

The failure demonstrated that Terraform apply is not an all-or-nothing transactional rollback.

The recovery sequence was:

```text
initial apply
    ↓
most resources created
    ↓
SNS subscription rejected
    ↓
successful resources retained in state
    ↓
input corrected
    ↓
terraform apply
    ↓
1 resource added
0 changed
0 destroyed
```

Terraform converged without rebuilding the already-correct infrastructure.

### Convergence Verification

After the first successful deployment:

```text
terraform plan
```

reported:

```text
No changes. Your infrastructure matches the configuration.
```

This verified alignment between:

```text
Terraform configuration
Terraform state
real AWS infrastructure
```

at that point in time.

### Destroy Verification

Terraform produced:

```text
Plan: 0 to add, 0 to change, 39 to destroy.
```

The environment was then deliberately destroyed.

Final result:

```text
Destroy complete! Resources: 39 destroyed.
```

Afterward:

```text
terraform state list
```

returned no managed resources.

A fresh plan then reported:

```text
Plan: 39 to add, 0 to change, 0 to destroy.
```

This proved that the infrastructure could be removed completely while its desired state remained encoded in Terraform.

### Reproducibility Verification

The complete environment was created again from the empty Terraform state.

The recreated environment received different AWS-generated identities.

First Terraform deployment:

```text
VPC → vpc-0f592ca583c27082c
EC2 → i-055886e195cd03b15
```

Second Terraform deployment:

```text
VPC → vpc-080e125e9f9dcfacc
EC2 → i-02b361873b71f41ab
```

This demonstrated:

```text
same configuration
        ↓
different physical resources
        ↓
same architecture
```

The second deployment's ALB target ultimately returned:

```text
healthy
```

and Terraform again reported:

```text
No changes. Your infrastructure matches the configuration.
```

### Readiness Investigation

During the recreated deployment, the ALB initially reported:

```text
Target.FailedHealthChecks
unhealthy
```

The infrastructure was diagnosed before any configuration was changed.

Evidence showed:

```text
EC2       → running
SSM       → Online
cloud-init → running
```

The bootstrap log also showed that:

```text
database password retrieval succeeded
container images were pulled
RDS migration succeeded
backend startup had begun
```

The first health inspection occurred before Nginx startup had completed.

No security-group change was required.

After bootstrap completed:

```text
ALB target → healthy
```

This demonstrated:

```text
infrastructure exists
        ≠
application ready
```

and:

```text
EC2 running
        ≠
application health check ready
```

### Git and State Hygiene

Terraform-generated and sensitive local files are excluded from version control:

```text
.terraform/
*.tfstate
*.tfstate.*
*.tfplan
*.tfvars
*.tfvars.json
```

The repository retains:

```text
.terraform.lock.hcl
terraform.tfvars.example
```

This separates reproducible configuration from local state and credentials.

### Lessons

- Terraform configuration, Terraform state, and real AWS infrastructure are related but distinct.
- An AWS resource existing does not mean Terraform manages it.
- Terraform does not automatically adopt manually created infrastructure based on names or tags.
- Resource references build a dependency graph and remove the need to copy AWS IDs manually.
- Values marked only `sensitive` can still exist in state; ephemeral and write-only values provide stronger secret handling where supported.
- A failed apply can leave successfully created resources managed in state.
- Rerunning Terraform after correcting the cause allows the environment to converge.
- `terraform plan` returning no changes is evidence of convergence at that moment.
- `terraform destroy` follows the dependency graph in reverse and can remove the environment without a manually ordered teardown procedure.
- Infrastructure provisioning and application readiness are separate operational states.
- Health checks, cloud-init state, bootstrap logs, Docker state, and Systems Manager provide different diagnostic evidence.
- Security rules should not be changed merely because a health check is temporarily failing.
- Infrastructure as Code becomes substantially more convincing when destroy and clean recreation are actually tested.
- AWS-generated resource identifiers should be treated as replaceable implementation details rather than durable configuration.

### Current Limitations

The Terraform deployment remains a learning and portfolio environment.

Current limitations include:

- Terraform state remains local.
- Shared remote-state locking is not yet configured.
- The application EC2 instance remains in a public subnet.
- Only one application instance is deployed.
- RDS remains Single-AZ.
- HTTP is used instead of HTTPS.
- There is no Auto Scaling Group.
- Application logs are not yet centralized.
- EC2 initialization still uses user data rather than image baking or dedicated configuration management.
- Supporting container images still use mutable tags.
- SNS email subscription confirmation remains a human step.
- Alert-email input validation can be improved further.
- No AWS WAF is configured.

### Verified

- Terraform successfully modeled the manually understood Sprint 8 AWS architecture.
- Terraform created 39 AWS resources from an empty state.
- IAM policy-document data sources were evaluated separately from provisioned AWS resources.
- EC2 successfully registered with Systems Manager.
- EC2 retrieved the database password from SSM Parameter Store.
- The immutable backend image was successfully downloaded from GHCR.
- Nginx and MySQL support images were successfully downloaded.
- The SQL migration successfully executed against private Amazon RDS.
- The ALB target became healthy after application bootstrap completed.
- Terraform reported zero changes after deployment.
- Terraform destroyed all 39 managed AWS resources.
- Terraform state contained no managed resources after destruction.
- Terraform correctly planned all 39 resources again from empty state.
- The second apply created new AWS resource identities.
- The recreated ALB target became healthy.
- Terraform again reported zero changes after recreation.

### Sprint Outcome

Sprint 8 answered:

> Can OpsBoard be deployed, secured, monitored, diagnosed, and recovered manually on AWS?

Sprint 9 answered:

> Can that understood architecture be encoded, destroyed, and recreated reproducibly from infrastructure configuration?

The verified lifecycle is now:

```text
manual architecture understanding
        ↓
Terraform modeling
        ↓
terraform apply
        ↓
automated application bootstrap
        ↓
healthy AWS environment
        ↓
terraform plan
        ↓
zero drift
        ↓
terraform destroy
        ↓
39 resources removed
        ↓
empty state
        ↓
terraform apply
        ↓
new physical resources
        ↓
same architecture
        ↓
healthy target
        ↓
zero drift
```

OpsBoard has therefore progressed from manually provisioned cloud infrastructure to a reproducible Terraform-managed AWS environment.

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
