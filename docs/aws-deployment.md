# AWS Deployment

## Overview

Sprint 8 moved OpsBoard from a locally reproducible release environment into a manually provisioned AWS deployment.

The objective was not simply to make the API reachable from the Internet.

The objective was to understand and verify the infrastructure layers required to operate the existing release artifact in AWS:

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
RDS MySQL
```

The deployment deliberately remained manual during this sprint.

Terraform is reserved for the next phase so the AWS resources, traffic paths, security boundaries, failure modes, and operational signals are understood before they are encoded as Infrastructure as Code.

---

## Architecture

The deployed architecture is:

```text
                         Internet
                            │
                            │ HTTP :80
                            ▼
                 ┌─────────────────────┐
                 │ Application Load    │
                 │ Balancer            │
                 │ Public Subnets A/B  │
                 └──────────┬──────────┘
                            │
                         TCP :80
                            │
                            ▼
                 ┌─────────────────────┐
                 │ EC2 t3.micro        │
                 │ Public Subnet A     │
                 │                     │
                 │ Nginx :80           │
                 │      ↓              │
                 │ Gunicorn :8000      │
                 │      ↓              │
                 │ Flask API           │
                 └──────────┬──────────┘
                            │
                         TCP :3306
                            │
                            ▼
                 ┌─────────────────────┐
                 │ RDS MySQL 8.0       │
                 │ db.t4g.micro        │
                 │ Private DB Subnets  │
                 │ Public access: No   │
                 └─────────────────────┘
```

Administration is performed through AWS Systems Manager Session Manager.

```text
Ubuntu workstation
      ↓
AWS CLI
      ↓
AWS Systems Manager
      ↓
EC2
```

No inbound SSH access is required.

---

## VPC and Networking

OpsBoard uses a dedicated VPC with CIDR:

```text
10.0.0.0/16
```

Four subnets were created across two Availability Zones:

```text
Public subnet A      10.0.1.0/24
Public subnet B      10.0.2.0/24

Private DB subnet A  10.0.11.0/24
Private DB subnet B  10.0.12.0/24
```

The public subnets route Internet-bound traffic through an Internet Gateway.

The database subnets have no default route to the Internet.

No NAT Gateway was introduced during this sprint in order to keep the lab architecture cost-conscious.

The RDS database remains reachable from the application tier through the VPC-local route.

This reinforced the distinction:

```text
Route table
→ Where can traffic go?

Security group
→ Which traffic is allowed?
```

---

## Security Groups

Traffic between tiers is restricted using security-group references.

```text
Internet
    ↓ TCP 80
ALB Security Group
    ↓ TCP 80
EC2 Security Group
    ↓ TCP 3306
RDS Security Group
```

The rules follow this model:

```text
ALB
Inbound TCP 80
Source: Internet

EC2
Inbound TCP 80
Source: ALB security group

RDS
Inbound TCP 3306
Source: EC2 security group
```

The EC2 instance does not expose:

```text
SSH :22
Gunicorn :8000
```

to the Internet.

Gunicorn is published only on the EC2 loopback interface:

```text
127.0.0.1:8000
```

Nginx is therefore the host-level HTTP entry point.

---

## Security-Boundary Verification

The EC2 instance has a public IPv4 address for the lab environment, but the security group prevents Internet clients from bypassing the load balancer.

This was tested explicitly.

Direct EC2 request:

```text
Internet → EC2 public IP :80
→ connection timeout
```

Load-balanced request:

```text
Internet → ALB → EC2 :80
→ 200 OK
```

This demonstrated that possessing a public IP does not automatically make the application publicly reachable.

The security-group rules still control the permitted traffic path.

---

## EC2 Application Runtime

The EC2 host runs Docker.

The exact backend artifact produced by the Sprint 7 CI/CD pipeline was deployed from GitHub Container Registry using its immutable Git commit SHA tag.

The runtime consists of:

```text
Nginx container
      ↓
Docker network
      ↓
backend alias
      ↓
Gunicorn
      ↓
Flask
```

The backend uses:

```text
Gunicorn 26.2.0
2 workers
port 8000
```

Both application containers use:

```text
--restart unless-stopped
```

so Docker can restore the runtime following an EC2 restart.

Application configuration is supplied at runtime through a root-readable environment file on the host rather than being embedded in the container image.

Secrets and infrastructure credentials are not stored in the Git repository.

---

## RDS MySQL

The database tier uses:

```text
Amazon RDS
MySQL 8.0
db.t4g.micro
Single-AZ
20 GiB gp3
encrypted storage
publicly accessible: false
```

The database subnet group spans two Availability Zones even though the current database deployment is Single-AZ.

Connectivity was verified progressively:

```text
DNS resolution
    ↓
TCP :3306
    ↓
MySQL authentication
    ↓
database existence
    ↓
schema existence
    ↓
application query
```

This prevented networking, authentication, schema, and application failures from being treated as the same problem.

---

## Database Migration

The existing version-controlled migration:

```text
db/migrations/001_create_incidents.sql
```

was applied to RDS.

Before migration:

```text
database reachable
mydatabase exists
incidents table absent
```

After migration:

```text
SHOW TABLES
→ incidents
```

The table structure was verified and the database initially contained zero incidents.

A migration troubleshooting exercise also reinforced the difference between authentication and networking failures.

The MySQL client initially reported:

```text
using password: NO
```

The problem was traced to the password not being supplied to the client process rather than to a security-group or RDS connectivity failure.

---

## Application Load Balancer

An Internet-facing Application Load Balancer distributes HTTP traffic to the EC2 application host.

The target group uses:

```text
Protocol: HTTP
Port: 80
Health path: /api/health
Target type: instance
```

Successful public verification returned:

```text
GET /api/health
→ 200 OK

GET /api/incidents
→ 200 OK
```

The request path was therefore verified end-to-end:

```text
Internet
    ↓
ALB
    ↓
EC2 security group
    ↓
Nginx
    ↓
Gunicorn
    ↓
Flask
    ↓
RDS
```

---

## Failure and Recovery Testing

Operational behavior was deliberately tested rather than assumed.

### Nginx Failure

Nginx was intentionally stopped while the backend container and database remained available.

The resulting telemetry showed:

```text
ALB target
→ unhealthy

TargetConnectionErrorCount
→ increased

HTTPCode_ELB_502_Count
→ increased
```

This demonstrated that the load balancer could select the target but could not establish the required connection to Nginx.

After Nginx was restarted:

```text
EC2-local health
→ 200 OK

ALB target
→ healthy

public API
→ 200 OK
```

---

### No Healthy Backend

When the application host was unavailable for a longer period, the public ALB continued receiving requests while it had no usable backend.

CloudWatch recorded:

```text
HTTPCode_ELB_503_Count
→ increased
```

This established a useful distinction:

```text
502
→ target selected but backend communication failed

503
→ no usable backend available
```

The public ALB also received unsolicited traffic while the application tier was unavailable, reinforcing the principle that Internet-facing infrastructure should be treated as publicly discoverable even when its DNS name has not been intentionally advertised.

---

## CloudWatch Observability

Native AWS metrics were used before introducing additional monitoring agents.

### ALB

Observed metrics included:

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

The deliberate Nginx outage was visible historically through CloudWatch.

The metrics independently recorded the transition from:

```text
healthy
→ unhealthy
→ recovered
```

---

### EC2

Observed metrics included:

```text
CPUUtilization
CPUCreditBalance
StatusCheckFailed_Instance
StatusCheckFailed_System
```

During the observation window:

```text
CPU utilization
→ very low

CPU credit balance
→ steadily increasing

instance status failures
→ 0

system status failures
→ 0
```

This demonstrated that application failure can occur while the EC2 infrastructure itself remains healthy.

---

### RDS

Observed metrics included:

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

The small lab workload showed:

```text
steady-state CPU
→ low

free storage
→ substantial headroom

swap usage
→ negligible

CPU credits
→ rebuilding after restart

surplus credits charged
→ 0
```

A deliberately long-lived MySQL connection was also used to verify that `DatabaseConnections` became visible in CloudWatch.

This demonstrated that telemetry publication can lag behind the event being observed.

---

## CloudWatch Alarms

Three alarms were created:

```text
opsboard-alb-unhealthy-target
opsboard-ec2-status-check-failed
opsboard-rds-low-storage
```

They cover three different operational concerns:

```text
Application availability
→ ALB unhealthy target

Compute/platform health
→ EC2 status check failure

Database capacity
→ low RDS free storage
```

The ALB alarm requires two consecutive one-minute unhealthy datapoints before entering `ALARM`.

This reduces sensitivity to very short transient events.

---

## SNS Notification Flow

An SNS topic provides the notification channel:

```text
CloudWatch Alarm
      ↓
SNS topic
      ↓
Email subscription
```

The SNS path was first tested independently.

A test message successfully reached the configured email endpoint.

The ALB alarm was then configured with both:

```text
ALARM action
OK action
```

A deliberate Nginx failure produced:

```text
UnHealthyHostCount = 1
      ↓
CloudWatch = ALARM
      ↓
SNS action executed
```

After Nginx recovery:

```text
ALB target = healthy
      ↓
CloudWatch = OK
      ↓
SNS recovery action executed
```

CloudWatch alarm history confirmed successful execution of both actions.

SNS CloudWatch metrics independently confirmed:

```text
NumberOfMessagesPublished
→ successful

NumberOfNotificationsDelivered
→ successful

NumberOfNotificationsFailed
→ 0
```

This completed the operational loop:

```text
Observe
   ↓
Detect
   ↓
Alert
   ↓
Diagnose
   ↓
Repair
   ↓
Recover
   ↓
Verify
```

---

## Cost Management

The AWS environment was treated as a metered engineering lab.

A monthly AWS Budget was configured.

Cost-conscious design choices included:

- no NAT Gateway;
- `t3.micro` EC2;
- `db.t4g.micro` RDS;
- Single-AZ RDS;
- small gp3 volumes;
- native CloudWatch metrics before additional agents;
- stopping EC2 and RDS when they are not needed;
- monitoring burstable-instance CPU credits.

One important operational lesson was that an Application Load Balancer cannot be stopped.

It continues to incur charges until it is deleted.

Stopped EC2 and RDS instances can also retain storage charges.

Cost therefore needs to be treated as another operational signal rather than something checked only after deployment.

---

## Current Limitations

This is a learning and portfolio deployment, not a production-ready architecture.

Current limitations include:

- application EC2 remains in a public subnet;
- only one application instance is deployed;
- RDS is Single-AZ;
- HTTP is used instead of HTTPS;
- no Auto Scaling Group is present;
- deployment infrastructure was created manually;
- application logs are not yet centralized in CloudWatch Logs;
- secrets remain host-managed rather than being retrieved dynamically from a dedicated secret-management service;
- no Web Application Firewall is configured.

These are deliberate boundaries of the sprint rather than claims of production completeness.

---

## Sprint Outcome

Sprint 8 demonstrated that the exact container artifact produced by the existing CI/CD pipeline could be deployed and operated in AWS.

The sprint established practical experience with:

- VPC networking;
- public and private subnets;
- route tables;
- Internet Gateway routing;
- security-group references;
- EC2;
- Systems Manager Session Manager;
- Docker on EC2;
- GitHub Container Registry deployment;
- RDS MySQL;
- database migration;
- Application Load Balancer;
- health checks;
- CloudWatch metrics;
- CloudWatch alarms;
- SNS notifications;
- controlled failure testing;
- recovery verification;
- AWS cost awareness.

Most importantly, the infrastructure was not treated as a collection of isolated AWS services.

It was tested as an operating system:

```text
traffic
→ routing
→ security
→ compute
→ containers
→ application
→ database
→ telemetry
→ alarm
→ notification
```

The next phase is to reproduce this architecture declaratively with Terraform.

```text
Sprint 8
Manual AWS deployment
        ↓
understand resources and failure modes
        ↓
Sprint 9
Terraform Infrastructure as Code
        ↓
reproducible infrastructure
```