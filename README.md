# OpsBoard

OpsBoard is a production-inspired incident management platform built to demonstrate modern DevOps engineering practices.

This project is being developed incrementally, following real-world engineering workflows, from a simple Flask API to a production-ready platform deployed on AWS with automated CI/CD and Kubernetes.

---

## Project Goals

- Learn Docker and Docker Compose
- Build production-quality containerized applications
- Deploy to AWS
- Automate deployments with GitHub Actions
- Provision infrastructure using Terraform
- Orchestrate services with Kubernetes
- Document engineering decisions and architecture

---

## Current Status

Sprint 2 (In Progress)

Current functionality:

- Health endpoint
- Incident API
- Hardcoded incident data

Upcoming:

- Dockerfile
- Docker Compose
- Nginx reverse proxy
- MySQL
- AWS deployment

---

## Technology Stack

- Python
- Flask
- Docker (coming next)
- Docker Compose (planned)
- Nginx (planned)
- MySQL (planned)
- AWS (planned)
- GitHub Actions (planned)
- Terraform (planned)
- Kubernetes (planned)

---

## Repository Structure

```
opsboard/

backend/
frontend/
nginx/
docs/

compose.yaml
README.md
```

---

## API Endpoints

| Method | Endpoint | Description |
|---------|----------|-------------|
| GET | /api/health | Health check |
| GET | /api/incidents | List all incidents |
| GET | /api/incidents/<id> | Retrieve one incident |

---

## Roadmap

- [x] Build initial Flask API
- [ ] Containerize backend
- [ ] Add Docker Compose
- [ ] Add Nginx reverse proxy
- [ ] Add MySQL persistence
- [ ] Deploy to AWS EC2
- [ ] Build CI/CD pipeline
- [ ] Provision infrastructure with Terraform
- [ ] Deploy to Kubernetes

---

This project is part of my journey toward becoming a Cloud & DevOps Engineer.