# Terraform Remote State and Workflow Hardening

## Overview

Sprint 10 hardened OpsBoard's Terraform workflow by moving the main infrastructure state from local workstation storage to a protected Amazon S3 backend.

Sprint 9 established that the AWS environment could be created, destroyed, and recreated reproducibly with Terraform.

Sprint 10 focused on a different problem:

```text
How should Terraform state itself be stored,
protected,
shared,
recovered,
and validated?
```

The sprint introduced:

- dedicated Terraform bootstrap infrastructure;
- Amazon S3 remote state;
- S3-native Terraform state locking;
- S3 versioning for state recovery;
- explicit server-side encryption;
- S3 public-access blocking;
- Terraform destruction protection for the state bucket;
- isolated state-recovery testing;
- Terraform validation in GitHub Actions;
- required Terraform CI checks on the protected `main` branch.

The result is a Terraform workflow that is safer for collaboration and more resilient to state loss or concurrent operations.

---

## Why Local State Was Not Enough

Before Sprint 10, the OpsBoard Terraform state was stored locally.

Conceptually:

```text
Developer workstation
        |
        v
terraform.tfstate
```

This works for a single-user learning environment, but it introduces several limitations.

### Security

Terraform state can contain infrastructure metadata and potentially sensitive values.

Committing state to GitHub would therefore be inappropriate.

### Collaboration

If multiple engineers maintain separate local copies of state, they can develop different views of the same AWS environment.

```text
Engineer A state
        \
         > same AWS environment
        /
Engineer B state
```

Those independent state histories can lead to conflicting infrastructure operations.

### Concurrency

Two Terraform processes modifying the same environment simultaneously can interfere with each other unless state modification is locked.

### Recovery

A single local state file provides limited recovery options if it is accidentally corrupted, overwritten, or deleted.

Sprint 10 addressed these concerns by moving the main state to a versioned and lockable S3 backend.

---

## Bootstrap Problem

Terraform cannot normally use an S3 backend before the S3 bucket exists.

A configuration such as:

```hcl
terraform {
  backend "s3" {
    bucket = "example-state-bucket"
  }
}

resource "aws_s3_bucket" "state" {
  bucket = "example-state-bucket"
}
```

contains a circular dependency.

Terraform must initialize the backend before it can run:

```text
terraform plan
terraform apply
```

but the bucket would only be created during:

```text
terraform apply
```

The dependency becomes:

```text
S3 bucket must exist
        ↓
terraform init can succeed

but

terraform apply must run
        ↓
S3 bucket can be created
```

To break this cycle, OpsBoard now uses a separate Terraform root configuration.

---

## Terraform Root Separation

The infrastructure directory now contains two independent Terraform roots:

```text
infrastructure/
├── terraform-bootstrap/
│   └── remote-state infrastructure
│
└── terraform/
    └── OpsBoard application infrastructure
```

These configurations live in the same Git repository but maintain separate state ownership.

```text
terraform-bootstrap/
        ↓
Bootstrap State

terraform/
        ↓
OpsBoard Application State
```

This established an important Terraform concept:

```text
one Git repository
        ≠
one Terraform state
```

Each root has its own resource ownership and lifecycle.

---

## State Bucket Bootstrap

The bootstrap configuration creates four Terraform-managed resources:

```text
aws_s3_bucket
aws_s3_bucket_public_access_block
aws_s3_bucket_versioning
aws_s3_bucket_server_side_encryption_configuration
```

Although these all configure one physical S3 bucket, Terraform manages them as four resource objects.

The first bootstrap plan therefore produced:

```text
Plan: 4 to add, 0 to change, 0 to destroy.
```

After apply:

```text
terraform state list
```

returned the four bootstrap resources.

The bootstrap state itself initially used Terraform's local backend.

---

## State Bucket Protection

The state bucket was intentionally designed with multiple protections.

### Public Access Blocking

All four S3 public-access controls are enabled:

```text
BlockPublicAcls       = true
IgnorePublicAcls      = true
BlockPublicPolicy     = true
RestrictPublicBuckets = true
```

Terraform does not require a public S3 bucket.

Authorized access is performed through AWS credentials and IAM.

---

## Server-Side Encryption

Explicit S3 server-side encryption is configured using:

```text
AES256
```

This uses SSE-S3.

Although modern S3 already encrypts new objects by default, the Terraform configuration explicitly declares the intended encryption behavior instead of depending only on a platform default.

The deployed bucket was verified with:

```bash
aws s3api get-bucket-encryption
```

which reported:

```text
SSEAlgorithm = AES256
```

---

## State Versioning

S3 versioning is enabled on the Terraform state bucket.

Verification returned:

```text
Status = Enabled
```

Versioning allows earlier state object snapshots to remain available after new versions are written.

Conceptually:

```text
terraform.tfstate
├── version A
├── version B
└── version C ← current
```

This became important later during the recovery experiment.

---

## Accidental Destruction Protection

The state bucket contains:

```hcl
lifecycle {
  prevent_destroy = true
}
```

A deliberate destroy test was performed with:

```bash
terraform plan -destroy
```

Terraform calculated:

```text
Plan: 0 to add, 0 to change, 4 to destroy.
```

but then rejected the plan because the S3 bucket had:

```text
lifecycle.prevent_destroy
```

Terraform returned:

```text
Error: Instance cannot be destroyed
```

This demonstrated that the protection was active rather than merely declared in source code.

The bucket also uses:

```text
force_destroy = false
```

These controls solve different problems.

```text
prevent_destroy
→ Terraform guardrail against planned destruction

force_destroy = false
→ S3 bucket deletion is not allowed while objects remain
```

---

## Remote Backend Configuration

The main OpsBoard Terraform root now uses an S3 backend.

The backend defines:

```hcl
backend "s3" {
  key          = "opsboard/prod/terraform.tfstate"
  region       = "us-east-1"
  encrypt      = true
  use_lockfile = true
}
```

The bucket name is provided during initialization rather than committed directly into the backend block.

This allows the repository configuration to remain reusable while deployment-specific backend information stays outside the source file.

---

## State Migration

At the end of Sprint 9, the application infrastructure had been destroyed.

The local state still existed and contained metadata, but tracked:

```text
Resources: 0
```

Before migration, the state was backed up locally.

The main Terraform backend was then initialized against S3.

During verification, an important issue was discovered.

The newly initialized remote state initially appeared as:

```text
Serial: 0
Lineage:
Resources: 0
```

and an S3 object check returned:

```text
404 Not Found
```

This demonstrated that successful backend initialization alone was not sufficient evidence that the expected state object had been persisted.

The original Sprint 9 state remained safely preserved in the pre-migration backup:

```text
Serial: 168
Resources: 0
```

The backup and current remote state both tracked zero resources.

Because there were no active Terraform resource bindings to recover, the new empty remote state lineage was retained rather than using a forced state overwrite simply to preserve historical lineage metadata.

The final remote-state baseline became:

```text
remote state object exists
Resources: 0
AWS application environment absent
Terraform configuration defines 39 resources
```

A Terraform plan therefore correctly returned:

```text
Plan: 39 to add, 0 to change, 0 to destroy.
```

No application infrastructure was created during the migration.

---

## Independent AWS Verification

The state result was cross-checked against AWS rather than trusting Terraform alone.

Queries showed:

```text
opsboard-app EC2 → no matching active/stopped instance
opsboard-alb      → not found
opsboard-db       → not found
```

This agreed with:

```text
remote Terraform state → 0 resources
Terraform plan          → 39 to add
```

The configuration, state, and observed AWS environment were therefore consistent.

---

## S3 State Object Verification

The main state object was verified directly with S3.

The object exists at:

```text
opsboard/prod/terraform.tfstate
```

The S3 metadata confirmed:

```text
ServerSideEncryption = AES256
VersionId             = present
```

This provided independent evidence that Terraform state was physically stored in the remote backend.

---

## Native S3 State Locking

The backend uses:

```hcl
use_lockfile = true
```

Terraform therefore uses an S3 object with the key:

```text
opsboard/prod/terraform.tfstate.tflock
```

for native state locking.

No DynamoDB state-lock table is used.

---

## Lock Lifecycle Verification

Terraform logging was enabled during a plan operation.

The logs showed:

```text
Attempting to lock remote state
Locked remote state
Unlocked remote state
```

This proved that Terraform actively acquired and released the S3-native lock.

S3 version history also contained multiple historical versions of:

```text
terraform.tfstate.tflock
```

together with delete markers.

The sequence was therefore:

```text
Terraform operation starts
        ↓
.tflock created
        ↓
state locked
        ↓
operation runs
        ↓
.tflock deleted
        ↓
lock released
```

Because S3 versioning is enabled, the historical lock-file activity remains observable even after the active lock object is removed.

---

## Concurrent Writer Experiment

State locking was tested deliberately with two Terraform processes.

Terminal A started a Terraform plan.

Terraform logging was monitored until the process reported:

```text
Locked remote state
```

The process was then paused with a Unix process signal while it still held the lock.

Conceptually:

```text
Terminal A
terraform plan
        ↓
lock acquired
        ↓
process paused
        ↓
lock remains active
```

Terminal B then attempted:

```bash
terraform plan -lock-timeout=5s
```

Terraform waited for the lock and failed with:

```text
Error acquiring the state lock
```

S3 returned:

```text
412 PreconditionFailed
```

The lock information identified the existing Terraform operation.

This demonstrated:

```text
Terraform writer A
        ↓
owns state lock

Terraform writer B
        ↓
cannot obtain same lock
        ↓
operation blocked
```

After Terminal A resumed and completed, Terraform released the lock.

A later plan from Terminal B succeeded normally.

This was direct evidence that concurrent state writers were prevented rather than merely a configuration assumption.

---

## Why `-lock=false` Was Not Used

Terraform reported that locking could be disabled with:

```text
-lock=false
```

That option was deliberately not used.

Bypassing the state lock would defeat the concurrency protection Sprint 10 was designed to establish.

Likewise, `force-unlock` was not used while the original process still legitimately owned the lock.

The operational lesson was:

```text
lock error
        ≠
immediately force-unlock
```

A lock must first be investigated to determine whether another valid Terraform process still owns it.

---

## State Version Recovery Lab

The main OpsBoard state was intentionally not modified for recovery testing.

Instead, an isolated Terraform state key was created:

```text
opsboard/labs/recovery.tfstate
```

The lab used Terraform's built-in:

```text
terraform_data
```

resource.

This allowed state behavior to be tested without creating AWS infrastructure.

---

## Recovery State Version 1

The initial lab configuration stored:

```text
input = "version-1"
```

Terraform apply created the first S3 state version.

The state showed:

```text
Serial: 1
Input: version-1
```

---

## Recovery State Version 2

The configuration was changed to:

```text
input = "version-2"
```

Terraform applied an in-place state change.

S3 then contained two versions of:

```text
opsboard/labs/recovery.tfstate
```

The downloaded state snapshots showed:

```text
Older state
Serial: 1
Lineage: same lineage
Input: version-1
```

and:

```text
Newer state
Serial: 2
Lineage: same lineage
Input: version-2
```

This demonstrated:

```text
same lineage
        ↓
same logical Terraform state

different serial
        ↓
different state generations
```

---

## Restoring an Older State Version

The older S3 object version was retrieved and copied back onto the same state key.

This produced a new S3 object version whose contents represented the older Terraform state.

The distinction was:

```text
new S3 VersionId
        ≠
new Terraform state serial
```

S3 considered the restored object the newest object version.

Terraform considered its contents the older state:

```text
input = version-1
```

The configuration still declared:

```text
input = version-2
```

Terraform plan therefore correctly detected:

```text
version-1 → version-2
```

and reported:

```text
Plan: 0 to add, 1 to change, 0 to destroy.
```

This proved that the historical state snapshot had actually been restored.

---

## Recovery Back to Desired State

Terraform apply was then run normally.

The desired configuration returned the state to:

```text
version-2
```

A final plan reported:

```text
No changes. Your infrastructure matches the configuration.
```

S3 now contained four historical state-object versions representing the complete exercise.

The tested recovery sequence was:

```text
state version 1
        ↓
state version 2
        ↓
restore version 1
        ↓
Terraform detects difference
        ↓
apply desired configuration
        ↓
state returns to version 2
        ↓
No changes
```

This demonstrated both version retention and usable state recovery.

---

## S3 Prefix Investigation

During version inspection, an initial S3 query used the prefix:

```text
opsboard/prod/terraform.tfstate
```

This returned versions for both:

```text
terraform.tfstate
terraform.tfstate.tflock
```

because the lock object begins with the same prefix.

This initially made the result appear to contain many Terraform state versions.

The query was then corrected to filter by exact key.

The lesson was:

```text
S3 prefix match
        ≠
exact object-key match
```

Evidence should be interpreted carefully rather than accepted purely because a command succeeded.

---

## Terraform CI

Sprint 10 added a dedicated GitHub Actions workflow:

```text
.github/workflows/terraform.yml
```

It validates both Terraform roots independently using a matrix:

```text
terraform-ci
├── infrastructure/terraform-bootstrap
└── infrastructure/terraform
```

Each matrix job performs:

```text
Checkout
    ↓
Install Terraform 1.16.1
    ↓
terraform fmt -check -recursive
    ↓
terraform init -backend=false
    ↓
terraform validate
```

---

## Why CI Uses `-backend=false`

GitHub pull-request validation does not need to read or modify the live Terraform state.

Using:

```bash
terraform init -backend=false
```

allows Terraform to initialize provider dependencies for validation without connecting to the S3 backend.

Therefore the pull-request validation workflow requires:

```text
no AWS credentials
no S3 access
no Terraform state access
no infrastructure deployment
```

The CI job answers:

```text
Is the Terraform formatted correctly?
Is the configuration internally valid?
```

It does not answer:

```text
What AWS changes would occur?
```

That distinction keeps validation safe and credential-free.

---

## Terraform CI Verification

The workflow was first validated locally.

Both roots passed:

```text
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
```

The feature branch was then pushed and Pull Request #16 was opened.

GitHub Actions ran both Terraform matrix jobs on fresh runners.

Both passed:

```text
terraform-ci (infrastructure/terraform)
terraform-ci (infrastructure/terraform-bootstrap)
```

The existing application CI also remained healthy:

```text
backend-ci        → success
integration-tests → success
```

The image publishing job remained skipped on the pull request, as intended.

---

## Required Terraform Status Checks

The two Terraform matrix checks were added to `main` branch protection.

The required pull-request checks are now:

```text
backend-ci
integration-tests
terraform-ci (infrastructure/terraform)
terraform-ci (infrastructure/terraform-bootstrap)
```

This means Terraform CI is not advisory.

A future pull request cannot merge into `main` while either Terraform root fails its required validation check.

---

## Merge Verification

Pull Request #16 was merged using a merge commit.

The merge commit was:

```text
808abfd8cc91190079fec75ed23ac08bf14d3d6f
```

Post-merge GitHub Actions on `main` completed successfully.

The results were:

```text
Terraform CI
├── infrastructure/terraform           → success
└── infrastructure/terraform-bootstrap → success

OpsBoard CI
├── backend-ci        → success
├── integration-tests → success
└── publish-image     → success
```

This demonstrated that the workflow remained healthy after integration into `main`.

---

## AWS Authentication Expiry

During several Sprint 10 operations, the authenticated AWS CLI session expired.

Terraform reported errors similar to:

```text
No valid credential sources found
login session has expired
```

The fix was to reauthenticate:

```bash
aws login --remote
```

The session expiry did not delete:

```text
S3 state
AWS resources
Terraform configuration
```

It only removed the local client's ability to authenticate until a new session was established.

This reinforced the distinction:

```text
authentication session
        ≠
infrastructure lifecycle
```

---

## Final Remote-State Verification

After the merge, the local Terraform working directory was reinitialized against the existing S3 backend.

Terraform then reported:

```text
Plan: 39 to add, 0 to change, 0 to destroy.
```

This was the expected result because:

```text
Terraform configuration → defines 39 application resources
Remote state            → tracks 0 application resources
AWS application stack   → currently absent
```

No apply was performed.

The remote state remained ready to reconstruct the environment when required.

---

## Sprint 10 Architecture

```text
                         GitHub
                           |
                           | Terraform source
                           v
                  +-------------------+
                  | Developer / CI    |
                  +---------+---------+
                            |
              +-------------+-------------+
              |                           |
              v                           v
   terraform-bootstrap/             terraform/
              |                           |
              | owns                      | owns
              v                           v
     S3 backend resources          OpsBoard AWS stack
              |
              v
     +-----------------------+
     | Amazon S3             |
     |                       |
     | terraform.tfstate     |
     | version history       |
     | terraform.tfstate     |
     | .tflock               |
     +-----------------------+
```

The ownership boundary is:

```text
Bootstrap Terraform
→ owns the infrastructure that stores state

Application Terraform
→ uses that backend and owns the OpsBoard application stack
```

---

## Key Engineering Lessons

- Terraform state is operational data and should not be treated as ordinary source code.
- GitHub is not an appropriate Terraform state backend.
- Separate Terraform roots can exist in the same repository while owning independent states.
- Backend infrastructure creates a bootstrap dependency that must be handled deliberately.
- An S3 state bucket should not be public.
- Encryption intent should be declared in infrastructure configuration.
- S3 versioning provides practical state-recovery capability.
- `prevent_destroy` is a Terraform guardrail, not an absolute AWS deletion control.
- `force_destroy` and `prevent_destroy` solve different problems.
- Successful `terraform init` is not sufficient proof that the expected remote state object exists.
- State verification should include both Terraform and backend-side evidence.
- State locking prevents concurrent Terraform writers.
- S3-native locking uses a `.tflock` object.
- S3 `412 PreconditionFailed` can be evidence of successful lock contention protection.
- `force-unlock` should not be used while a legitimate Terraform process still owns the lock.
- S3 object versions and Terraform state serial numbers represent different concepts.
- Restoring an older S3 object version can recover historical Terraform state contents.
- Recovery should be tested in an isolated state before touching important infrastructure state.
- S3 prefixes can match multiple related keys and should not be mistaken for exact-key queries.
- `terraform init -backend=false` makes credential-free CI validation possible.
- `terraform validate` does not create infrastructure.
- Required Terraform CI checks turn validation from advisory feedback into a merge gate.
- AWS authentication-session expiry does not destroy durable infrastructure or remote state.
- Troubleshooting should compare expected evidence with observed evidence rather than trusting successful command completion alone.

---

## Sprint 10 Outcome

Sprint 9 established:

```text
reproducible AWS infrastructure
```

Sprint 10 established:

```text
protected
remote
versioned
lockable
recoverable
CI-validated
Terraform state management
```

The progression is now:

```text
Application
    ↓
Containers
    ↓
Networking
    ↓
Persistence
    ↓
CI/CD
    ↓
AWS Deployment
    ↓
Observability
    ↓
Terraform Infrastructure as Code
    ↓
Remote State & Workflow Hardening
```

Terraform is no longer dependent on one workstation's local state file.

The project's Terraform workflow now has:

```text
centralized state
state history
concurrency protection
recovery capability
automated validation
protected merge gates
```

This completes Sprint 10.
