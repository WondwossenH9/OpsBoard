# OpsBoard

OpsBoard is a production-inspired incident management platform built to demonstrate modern DevOps and cloud engineering practices.

The project is being developed incrementally using real-world engineering workflows, progressing from a simple Flask REST API into a containerized multi-service platform with persistent data, reverse proxying, automated CI/CD, infrastructure as code, and eventually Kubernetes.

The goal is not simply to build an application, but to demonstrate how applications are developed, containerized, configured, operated, and progressively prepared for production environments.

---

## Project Goals

OpsBoard is being built to demonstrate practical skills in:

- Linux
- Git and GitHub
- Python and Flask
- Docker
- Docker Compose
- Container networking
- Nginx reverse proxying
- MySQL
- Persistent storage
- Application configuration and secrets
- CI/CD with GitHub Actions
- AWS
- Terraform
- Kubernetes
- Observability and operational practices

The emphasis is on understanding how these technologies work together rather than learning them in isolation.

---

## Current Status

**Sprint 5 — Database Integration & Multi-Service Architecture**

OpsBoard currently consists of three application services:

- **Nginx** — public reverse proxy
- **Flask** — backend REST API
- **MySQL** — persistent database

Docker Compose provides:

- Service-to-service networking
- Internal DNS resolution
- Service dependencies
- MySQL health checks
- Persistent named volumes
- Environment-based configuration

Only Nginx exposes a host port.

---

## Current Architecture

```text
                         Browser
                            |
                            | HTTP :80
                            v
                    +---------------+

                    |     Nginx     |
                    | Reverse Proxy |
                    +-------+-------+
                            |
                            | backend:8000
                            v
                    +---------------+

                    |     Flask     |
                    |   REST API    |
                    +-------+-------+
                            |
                            | mysql:3306
                            v
                    +---------------+

                    |     MySQL     |
                    |   Database    |
                    +-------+-------+
                            |
                            v
                    +---------------+

                    | mysql_data    |
                    | Named Volume  |
                    +---------------+
```

## Network Boundary

Only Nginx is exposed to the host:

`Host :80 → Nginx :80`

The following services remain internal to the Docker Compose network:

- **Flask**  → `:8000`
- **MySQL**  → `:3306`

Flask communicates with MySQL using the Compose service name `mysql:3306` rather than a hardcoded container IP.

This allows Docker Compose's internal DNS to resolve the MySQL service dynamically, even if the container's IP address changes.

## Application Features

### Root Endpoint
`GET /`

Provides basic API information and available endpoints.

Example response:
```json
{
  "health": "/api/health",
  "incidents": "/api/incidents",
  "message": "Welcome to OpsBoard API",
  "status": "running",
  "version": "1.0.0"
}
```

### Health Check
`GET /api/health`

Returns the current service status and application metadata.

Example response:
```json
{
  "environment": "development",
  "service": "OpsBoard API",
  "status": "healthy",
  "version": "1.0.0"
}
```

### List Incidents
`GET /api/incidents`

Retrieves incidents from MySQL.

Example response:
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

### Retrieve an Incident
`GET /api/incidents/<id>`

Retrieves a specific incident from MySQL.

Example request: `GET /api/incidents/1`

Returns:
```json
{
  "id": 1,
  "severity": "high",
  "status": "investigating",
  "title": "Database Connection Timeout"
}
```

If the requested incident does not exist, the API returns `404 Not Found`.

Example error response:
```json
{
  "error": "Not Found",
  "message": "Incident with ID 999 was not found."
}
```

## Technology Stack

### Application
- Python 3.12
- Flask 3.1.1
- MySQL Connector/Python 9.4.0

### Containerization
- Docker
- Docker Compose
- Python 3.12 Slim
- MySQL 8.0
- Nginx Alpine

### Infrastructure
- Docker bridge networking
- Docker Compose internal DNS
- Docker named volumes
- Container health checks

### Planned
- GitHub Actions
- AWS
- Terraform
- Kubernetes
- Production WSGI server
- Observability and monitoring

## Configuration

Application and database configuration is supplied through environment variables. Local development uses a `.env` file.

The real `.env` file is intentionally excluded from version control. A `.env.example` file is provided as a configuration template.

Example configuration:
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

The Flask application reads the database configuration from environment variables rather than hardcoding credentials or container IP addresses.

## Persistent Storage

MySQL stores its data in a Docker named volume: `opsboard_mysql_data`

The volume is mounted inside the MySQL container at: `/var/lib/mysql`

This means database data survives MySQL container recreation. The project deliberately demonstrates the distinction between an **Ephemeral container** and **Persistent data**.

For example, running:
```bash
docker compose down
```
removes the containers but preserves the named volume.

By contrast, running:
```bash
docker compose down -v
```
also removes the named volume and therefore deletes the local database data.

## MySQL Health Check

Docker Compose uses a MySQL health check to determine when the database is ready to accept connections.

The backend depends on MySQL being healthy rather than merely having its container started:
```yaml
depends_on:
  mysql:
    condition: service_healthy
```

The health check uses `mysqladmin ping` to verify that MySQL is responding. This prevents a common startup race where the Flask application attempts to connect while MySQL is still initializing.

The distinction is important:
* **service_started** → Container process has started
* **service_healthy** → Application has passed its configured health check

## Repository Structure

```text
opsboard/
│
├── backend/
│   ├── app.py
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .dockerignore
│   └── README.md
│
├── frontend/
│   └── README.md
│
├── nginx/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── README.md
│
├── docs/
│   ├── engineering-journal.md
│   └── README.md
│
├── .env.example
├── .gitignore
├── compose.yaml
├── CHANGELOG.md
└── README.md
```

The project is intentionally organized into separate areas for:
- Backend application
- Frontend application
- Reverse proxy
- Engineering documentation
- Infrastructure orchestration

This structure will allow each area to evolve independently as the project grows.

## Running Locally

1. Clone the repository and enter the project directory.
2. Create a local environment file:
   ```bash
   cp .env.example .env
   ```
3. Update the values in `.env` as required.
4. Start the platform:
   ```bash
   docker compose up -d --build
   ```
5. Check service status:
   ```bash
   docker compose ps
   ```

The expected architecture layout is:
```text
opsboard-nginx
       |
       +----> opsboard-backend
                    |
                    +----> opsboard-mysql
```

The API is available through Nginx at `http://localhost`.

### Testing Endpoints

Test the root endpoint:
```bash
curl http://localhost/
```

Test the health endpoint:
```bash
curl http://localhost/api/health
```

List incidents:
```bash
curl http://localhost/api/incidents
```

Retrieve a specific incident:
```bash
curl http://localhost/api/incidents/1
```

Test the not-found response:
```bash
curl http://localhost/api/incidents/999
```

## Useful Docker Commands

| Action | Command |
| :--- | :--- |
| Start the platform | `docker compose up -d` |
| Rebuild and start | `docker compose up -d --build` |
| View service status | `docker compose ps` |
| View all service logs | `docker compose logs` |
| Follow service logs | `docker compose logs -f` |
| View backend logs | `docker compose logs backend` |
| View MySQL logs | `docker compose logs mysql` |
| View Nginx logs | `docker compose logs nginx` |
