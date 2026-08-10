# Changelog

## v0.3.0 — Reverse Proxy Architecture

### Added

* Docker Compose orchestration
* Nginx reverse proxy
* Custom Nginx configuration
* Automatic Docker networking
* Internal service discovery using Docker Compose DNS
* Multi-container application architecture

### Improved

* Browser traffic now flows through Nginx instead of directly to the Flask application.
* Backend service is no longer exposed directly to the host.
* Project documentation updated to reflect the current architecture.

### Learned

* Docker Compose orchestration
* Reverse proxy architecture
* Internal Docker networking
* Docker Compose service discovery
* Difference between `depends_on` (startup order) and request routing (`proxy_pass`)

---

## v0.2.0 — Containerized Backend

### Added

* Dockerfile for the Flask backend
* Optimized Docker layer caching
* `.dockerignore`
* Containerized Flask API

### Learned

* Docker images and containers
* Docker build cache
* Port publishing
* Container networking basics

---

## v0.1.0 — API Foundation

### Added

* Initial Flask REST API
* Health endpoint
* Incident endpoints
* Project structure
* Initial documentation

### Learned

* Flask routing
* JSON responses
* Basic API design
* GitHub project initialization

---

## Next Release

**v0.4.0 – Persistent Data**

Planned features:

* MySQL integration
* Docker volumes
* Environment variables
* Persistent incident storage
* Database initialization
