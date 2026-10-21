# Terraform Infrastructure as Code

## Overview

Sprint 9 converted the manually understood AWS architecture from Sprint 8 into reproducible Infrastructure as Code using Terraform.

Sprint 8 deliberately provisioned the AWS environment manually so that networking, security boundaries, compute, database connectivity, load balancing, observability, failure modes, and cost behavior were understood before automation.

Sprint 9 then encoded that architecture declaratively.

The objective was not simply:

```text
terraform apply
→ AWS resources exist
```

The objective was to prove:

```text
Terraform configuration
        ↓
terraform apply
        ↓
working OpsBoard environment
        ↓
terraform plan
        ↓
zero drift
        ↓
terraform destroy
        ↓
environment removed
        ↓
terraform apply
        ↓
new AWS resources
        ↓
same working OpsBoard environment
```

The final result demonstrated that AWS-generated resource identities are disposable while the Terraform configuration remains the source of truth.

---

## Sprint Objective

The target reproducibility cycle was:

```text
terraform apply
        ↓
working OpsBoard
        ↓
terraform destroy
        ↓
infrastructure removed
        ↓
terraform apply
        ↓
working OpsBoard again
```

This required automating both:

```text
Infrastructure provisioning
```

and:

```text
EC2 application bootstrap
```

Provisioning an empty EC2 instance was not considered sufficient.

A clean deployment needed to produce a functioning application without manually connecting to EC2 and installing or configuring the runtime.

---

## Tooling

Sprint 9 used:

```text
Terraform 1.16.x
AWS Provider 6.69.x
AWS CLI
Amazon EC2
Amazon RDS
Application Load Balancer
AWS Systems Manager
CloudWatch
Amazon SNS
Docker
GitHub Container Registry
```

The Terraform configuration lives under:

```text
infrastructure/
└── terraform/
```

Key files include:

```text
versions.tf
providers.tf
variables.tf
networking.tf
security.tf
iam.tf
database.tf
compute.tf
load-balancer.tf
monitoring.tf
parameters.tf
user-data.sh.tftpl
terraform.tfvars.example
```

Terraform provider dependencies are pinned through:

```text
.terraform.lock.hcl
```

The local provider installation directory is excluded from version control.

Terraform state and real variable files are also excluded.

---

## Terraform Git Hygiene

The repository ignores:

```text
**/.terraform/*
*.tfstate
*.tfstate.*
*.tfplan
*.tfvars
*.tfvars.json
```

while deliberately retaining:

```text
.terraform.lock.hcl
*.tfvars.example
```

This establishes the distinction:

```text
Terraform configuration
→ version controlled

Provider lock file
→ version controlled

Real secrets / local variables
→ not version controlled

Local state
→ not version controlled
```

The example variable file documents required local inputs without containing real credentials.

---

## Architecture

Terraform reproduces the AWS architecture first established manually in Sprint 8.

```text
                         Internet
                            |
                            | HTTP :80
                            v
                 +----------------------+
                 | Application Load     |
                 | Balancer             |
                 | Public Subnets A/B   |
                 +----------+-----------+
                            |
                            | TCP :80
                            v
                 +----------------------+
                 | EC2 t3.micro         |
                 | Public Subnet A      |
                 |                      |
                 | Nginx :80            |
                 |     |                |
                 |     v                |
                 | Gunicorn :8000       |
                 |     |                |
                 |     v                |
                 | Flask REST API       |
                 +----------+-----------+
                            |
                            | TCP :3306
                            v
                 +----------------------+
                 | Amazon RDS MySQL     |
                 | db.t4g.micro         |
                 | Private DB Subnets   |
                 | Public access: No    |
                 +----------------------+
```

Operational services include:

```text
Systems Manager
CloudWatch
Amazon SNS
SSM Parameter Store
GitHub Container Registry
```

---

## Terraform Dependency Model

Terraform resources reference one another rather than hardcoding AWS-generated identifiers.

For example:

```hcl
subnet_id = aws_subnet.public_a.id
```

instead of:

```text
subnet-xxxxxxxxxxxxxxxxx
```

and:

```hcl
vpc_security_group_ids = [
  aws_security_group.ec2.id
]
```

instead of copying a security-group ID manually.

The resulting dependency graph includes relationships such as:

```text
VPC
 ↓
Subnets
 ↓
EC2
```

and:

```text
ALB security group
        ↓
EC2 security group
        ↓
RDS security group
```

and:

```text
RDS
 ↓
generated endpoint
 ↓
EC2 user-data template
 ↓
backend runtime configuration
```

Terraform therefore determines resource creation ordering from the declared relationships.

Explicit `depends_on` is used only where ordering is operationally important but not completely represented by direct attribute references.

EC2 waits for both:

```text
AmazonSSMManagedInstanceCore attachment
OpsBoard runtime-secret IAM policy
```

before launch.

---

## Networking

Terraform creates a dedicated VPC:

```text
10.0.0.0/16
```

Four subnets span two Availability Zones:

```text
Public subnet A      10.0.1.0/24
Public subnet B      10.0.2.0/24

Private DB subnet A  10.0.11.0/24
Private DB subnet B  10.0.12.0/24
```

The public subnets:

```text
public A
public B
    ↓
public route table
    ↓
0.0.0.0/0
    ↓
Internet Gateway
```

The database subnets use a separate private route table.

They have no Internet default route.

```text
private DB A
private DB B
    ↓
private route table
    ↓
VPC local route only
```

No NAT Gateway is used.

This preserves the cost-conscious Sprint 8 architecture.

---

## Security Groups

Terraform reproduces the tiered security model:

```text
Internet
    ↓ TCP 80
ALB Security Group
    ↓ TCP 80
EC2 Security Group
    ↓ TCP 3306
RDS Security Group
```

The rules use security-group references rather than broad internal CIDR ranges.

The application host does not expose:

```text
SSH :22
Gunicorn :8000
```

directly to the Internet.

Administration remains available through AWS Systems Manager Session Manager.

The EC2 instance receives a public IPv4 address for outbound Internet access in the lab environment, but inbound HTTP is restricted to the ALB security group.

---

## IAM and Systems Manager

Terraform creates:

```text
OpsBoardEC2Role
OpsBoardEC2InstanceProfile
```

The EC2 trust relationship allows:

```text
ec2.amazonaws.com
```

to assume the role.

The role receives the AWS-managed:

```text
AmazonSSMManagedInstanceCore
```

policy.

This enables Session Manager administration without an SSH key or inbound port `22`.

A separate least-privilege runtime policy permits EC2 to read only the OpsBoard database password parameter.

Conceptually:

```text
EC2 role
   |
   +-- Systems Manager core permissions
   |
   +-- ssm:GetParameter
           |
           v
      /opsboard/db/password
```

Broad:

```text
ssm:* on *
```

access is not granted.

---

## Database

Terraform creates:

```text
Amazon RDS MySQL 8.0
db.t4g.micro
20 GiB gp3
encrypted storage
Single-AZ
publicly accessible: false
```

The RDS subnet group uses:

```text
private DB subnet A
private DB subnet B
```

across two Availability Zones.

The database itself remains Single-AZ for the learning environment.

Application connectivity remains:

```text
EC2 security group
        ↓ TCP 3306
RDS security group
```

---

## Secret Handling

The database password is supplied locally through an ignored Terraform variable file.

The Terraform variable is:

```text
sensitive
ephemeral
```

The RDS resource uses a write-only password argument.

The SSM Parameter Store resource also uses a write-only value.

The intended secret flow is:

```text
local terraform.tfvars
        ↓
ephemeral Terraform value
        ├────────→ RDS password
        |
        └────────→ SSM SecureString
                          ↓
                    EC2 retrieves
                          ↓
              /etc/opsboard/backend.env
```

The real password is not committed to Git.

The EC2 bootstrap does not embed the password directly into user data.

Instead, the running instance retrieves it from:

```text
/opsboard/db/password
```

using its IAM role.

The host runtime environment file is stored at:

```text
/etc/opsboard/backend.env
```

with restrictive permissions.

---

## Immutable Application Artifact

Terraform does not rebuild the backend application.

The application host deploys the exact SHA-tagged image previously produced by the Sprint 7 CI/CD pipeline:

```text
ghcr.io/wondwossenh9/opsboard-backend:<git-commit-sha>
```

The deployment therefore preserves:

```text
Build once
    ↓
publish
    ↓
deploy the same artifact
```

Before the first Terraform deployment, anonymous GHCR access was explicitly tested.

The SHA-tagged backend image could be pulled after logging out of GHCR.

This proved that a fresh EC2 instance would not depend on interactive registry authentication.

---

## EC2 Application Bootstrap

Infrastructure creation alone was not considered sufficient.

Terraform renders:

```text
user-data.sh.tftpl
```

into EC2 user data.

A newly created EC2 instance automatically:

```text
installs Docker
        ↓
installs AWS CLI if required
        ↓
creates /etc/opsboard
        ↓
retrieves DB password from SSM
        ↓
creates backend.env
        ↓
restores version-controlled migration
        ↓
restores version-controlled Nginx config
        ↓
creates Docker network
        ↓
pulls backend image
        ↓
pulls Nginx
        ↓
pulls MySQL client image
        ↓
applies RDS migration
        ↓
starts backend
        ↓
starts Nginx
        ↓
verifies local /api/health
```

The bootstrap logs to:

```text
/var/log/opsboard-bootstrap.log
```

Shell tracing is deliberately not enabled because runtime secrets must not be echoed into bootstrap logs.

---

## Version-Controlled Runtime Files

The EC2 bootstrap does not maintain separate copies of the database migration or Nginx configuration.

Terraform reads the existing repository files:

```text
db/migrations/001_create_incidents.sql
nginx/nginx.conf
```

and supplies their contents to the EC2 bootstrap template.

This preserves one source of truth.

```text
repository file
      ↓
Terraform file()
      ↓
base64encode()
      ↓
EC2 user data
      ↓
restore exact file
```

Changes to those version-controlled files therefore change the EC2 bootstrap definition.

The EC2 resource is configured so changes to user data can trigger instance replacement rather than leaving an existing server with stale bootstrap configuration.

---

## Database Migration During Bootstrap

The version-controlled migration is applied directly to RDS before the application containers start.

The migration creates the:

```text
incidents
```

table.

The bootstrap retries database migration because:

```text
RDS resource exists
        ≠
database immediately ready for application traffic
```

The sequence is:

```text
RDS provisioned
      ↓
EC2 bootstrap
      ↓
migration attempt
      ↓
retry if necessary
      ↓
migration succeeds
      ↓
backend starts
```

A failed migration eventually terminates the bootstrap with a non-zero exit rather than silently starting the application against an unprepared schema.

---

## Load Balancing

Terraform creates an Internet-facing Application Load Balancer across both public subnets.

```text
public subnet A
        +
public subnet B
        ↓
Application Load Balancer
```

The listener accepts:

```text
HTTP :80
```

and forwards to:

```text
opsboard-tg
```

The target group uses:

```text
Protocol: HTTP
Port: 80
Target type: instance
```

The health check configuration is explicitly defined as:

```text
Path: /api/health
Protocol: HTTP
Port: traffic-port
Interval: 30 seconds
Timeout: 5 seconds
Healthy threshold: 2
Unhealthy threshold: 2
Matcher: 200
```

The EC2 instance is registered through a Terraform target-group attachment rather than by manually copying an instance ID.

---

## Observability and Alerting

Terraform creates three CloudWatch alarms:

```text
opsboard-alb-unhealthy-target
opsboard-ec2-status-check-failed
opsboard-rds-low-storage
```

They monitor three separate failure domains:

```text
Application availability
→ ALB unhealthy target

Compute/platform health
→ EC2 status-check failure

Database capacity
→ low RDS free storage
```

Terraform also creates:

```text
opsboard-alerts
```

as an SNS topic.

The ALB unhealthy-target alarm publishes both:

```text
ALARM
OK
```

state transitions to SNS.

The email endpoint remains a local Terraform input rather than being hardcoded in the repository.

AWS still requires human confirmation of a newly created email subscription.

---

## First Terraform Apply

Before the first apply, Terraform had:

```text
Configuration
→ 39 AWS resources declared

State
→ no state file

Existing manual AWS environment
→ removed
```

The manual Sprint 8 environment was deliberately dismantled before the first real Terraform build.

This ensured the deployment demonstrated clean infrastructure creation rather than merely importing existing resources.

Terraform then created the environment from code.

---

## Partial Apply and Recovery

The first apply encountered an SNS subscription error because the alert email input was not accepted by AWS.

The important result was that Terraform did not roll back all successfully created resources.

Instead:

```text
most resources created successfully
        ↓
SNS subscription failed
        ↓
successful resources retained in state
        ↓
input corrected
        ↓
terraform apply rerun
        ↓
only missing SNS subscription created
```

The second apply reported:

```text
Resources: 1 added, 0 changed, 0 destroyed.
```

This demonstrated Terraform convergence after partial failure.

A failed apply is not equivalent to an automatically rolled-back transaction.

Terraform state preserves successfully completed work.

---

## First Deployment Verification

After the first successful deployment, the ALB health check returned:

```text
200 OK
```

Terraform then refreshed the real AWS environment and reported:

```text
No changes. Your infrastructure matches the configuration.
```

This established:

```text
Terraform configuration
        =
Terraform state
        =
real AWS infrastructure
```

with no detected drift.

---

## Destroy Test

The next objective was to prove that the environment was disposable.

Terraform first produced the destroy plan:

```text
Plan: 0 to add, 0 to change, 39 to destroy.
```

The actual destroy then completed with:

```text
Destroy complete! Resources: 39 destroyed.
```

After destruction:

```text
terraform state list
```

returned no managed resources.

A new plan produced:

```text
Plan: 39 to add, 0 to change, 0 to destroy.
```

This demonstrated that:

```text
configuration remained
        ↓
state became empty
        ↓
real infrastructure was removed
        ↓
Terraform still knew how to rebuild everything
```

---

## Recreate Test

Terraform was then applied again from the empty state.

The recreated infrastructure received completely new AWS-generated identities.

For example, the first Terraform deployment used:

```text
VPC → vpc-0f592ca583c27082c
EC2 → i-055886e195cd03b15
```

After destroy and recreation:

```text
VPC → vpc-080e125e9f9dcfacc
EC2 → i-02b361873b71f41ab
```

The identifiers changed.

The architecture did not.

This demonstrates the central Infrastructure as Code principle:

```text
resource identity is disposable
        ↓
configuration is durable
```

---

## Recreate Readiness Investigation

During the second clean deployment, the ALB initially reported:

```text
Target.FailedHealthChecks
unhealthy
```

The infrastructure was not immediately modified.

Instead, diagnosis proceeded layer by layer.

EC2 reported:

```text
running
```

Systems Manager reported:

```text
Online
```

The bootstrap log showed:

```text
AWS CLI installed
DB password retrieved from SSM
backend configuration created
migration restored
Nginx configuration restored
Docker network created
backend image pulled
Nginx image pulled
MySQL image pulled
database migration succeeded
```

At the time of the first diagnostic check:

```text
cloud-init status
→ running
```

and the bootstrap had only reached:

```text
starting backend container
```

Nginx had not yet completed startup.

A local HTTP request to port `80` therefore failed temporarily.

No security-group change was made.

No Terraform rerun was used as a random repair attempt.

After bootstrap completed, ALB target health became:

```text
healthy
```

with no configuration change.

This established an important readiness distinction:

```text
EC2 running
        ≠
application ready
```

and:

```text
terraform apply complete
        ≠
all asynchronous application initialization already finished
```

Application readiness must be observed independently from infrastructure existence.

---

## Final Convergence Verification

After the second deployment completed, Terraform again reported:

```text
No changes. Your infrastructure matches the configuration.
```

The ALB target reported:

```text
healthy
```

The deployment therefore completed the full reproducibility cycle:

```text
Terraform configuration
        ↓
first apply
        ↓
working infrastructure
        ↓
zero-drift plan
        ↓
destroy 39 resources
        ↓
empty Terraform state
        ↓
plan 39 resources
        ↓
second apply
        ↓
new AWS resource IDs
        ↓
same architecture
        ↓
healthy ALB target
        ↓
zero-drift plan
```

---

## Resource Count

The Terraform configuration creates 39 AWS resources across the following areas:

```text
Networking
Security
IAM
Compute
Database
Load balancing
Secret storage
Monitoring
Alerting
```

Terraform data sources used to construct IAM policies are evaluated as part of the configuration but do not represent additional AWS resources being provisioned.

---

## Important Terraform Lessons

### Existing AWS Resources Are Not Automatically Managed

Before the first apply, the manually created Sprint 8 VPC already existed in AWS.

When the Terraform configuration first declared:

```text
aws_vpc.opsboard
```

Terraform still proposed:

```text
+ create
```

because:

```text
exists in AWS
        ≠
managed by Terraform
```

Terraform does not automatically adopt resources based on names or tags.

Existing resources require explicit import if they are to become Terraform-managed.

Sprint 9 deliberately chose clean recreation rather than import.

---

### Configuration, State, and Real Infrastructure Are Different

Terraform operates across three related but distinct concepts:

```text
Configuration
→ what should exist

State
→ what Terraform believes it manages

Real infrastructure
→ what AWS actually contains
```

Understanding the difference was essential during:

```text
initial planning
partial apply recovery
destroy
recreation
drift verification
```

---

### References Build the Dependency Graph

Terraform resource references remove the need to manually copy:

```text
VPC IDs
subnet IDs
security-group IDs
instance IDs
RDS endpoints
ALB ARN suffixes
```

The configuration expresses relationships instead.

This improves both reproducibility and deletion ordering.

---

### Apply Is Not a Transactional Rollback

The SNS failure demonstrated:

```text
one resource fails
        ≠
all successful resources disappear
```

Terraform records successfully created resources in state and continues toward convergence on the next apply.

---

### Infrastructure Health and Application Health Differ

The second deployment demonstrated:

```text
EC2 running
SSM Online
        ≠
Nginx ready
```

ALB health checks provided the application-level readiness signal.

---

### Evidence Before Intervention

The transient unhealthy target was diagnosed using:

```text
EC2 state
SSM PingStatus
ALB target-health reason
cloud-init state
bootstrap log
Docker state
local HTTP verification
```

Security groups were not changed without evidence.

Terraform was not blindly rerun.

The existing architecture had already worked, so the investigation focused on the layer whose evidence indicated incomplete readiness.

---

## Current Limitations

The Terraform environment remains a learning and portfolio deployment rather than a production-ready platform.

Current limitations include:

- Terraform state is local rather than stored in a remote backend.
- State locking is not yet provided through shared remote state infrastructure.
- Application EC2 remains in a public subnet.
- Only one application instance is deployed.
- RDS remains Single-AZ.
- HTTP is used instead of HTTPS.
- No Auto Scaling Group is present.
- Application logs are not centralized in CloudWatch Logs.
- The bootstrap uses EC2 user data rather than a dedicated configuration-management or image-baking workflow.
- The database password version is manually controlled.
- Supporting container images such as Nginx and MySQL are referenced by mutable version tags rather than immutable digests.
- Email subscription confirmation remains an external human step.
- The alert-email variable should receive stronger local validation to reject invalid input before the AWS API call.
- No Web Application Firewall is configured.

These are deliberate boundaries and future improvement opportunities rather than claims of production completeness.

---

## Sprint Outcome

Sprint 9 moved OpsBoard from:

```text
manually provisioned AWS infrastructure
```

to:

```text
declarative
reproducible
destroyable
recreatable
Terraform-managed infrastructure
```

The strongest verification was not the first successful apply.

It was:

```text
apply
    ↓
verify
    ↓
zero drift
    ↓
destroy
    ↓
empty state
    ↓
reapply
    ↓
new AWS identities
    ↓
same healthy application architecture
    ↓
zero drift
```

This demonstrated that the platform no longer depends on manually remembered AWS resource identifiers or one-off provisioning steps.

The infrastructure definition, application bootstrap, network relationships, security boundaries, runtime secret path, database migration, load balancing, monitoring, and alerting are now encoded as repeatable infrastructure configuration.

Sprint 8 established understanding.

Sprint 9 established reproducibility.
