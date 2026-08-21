# Changelog

All notable changes to OpsBoard are documented in this file.

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
- Backend waits for MySQL to become healthy before starting.
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