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
