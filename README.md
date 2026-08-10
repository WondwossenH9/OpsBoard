# OpsBoard

OpsBoard is a production-inspired incident management platform built to demonstrate modern DevOps engineering practices.

The project is being developed incrementally using real-world engineering workflows—from a simple Flask REST API to a production-ready cloud-native application deployed on AWS with automated CI/CD and Kubernetes.

---

## Project Goals

* Learn modern DevOps practices through a real project
* Build production-quality containerized applications
* Deploy applications to AWS
* Automate deployments using GitHub Actions
* Provision infrastructure with Terraform
* Orchestrate containers using Kubernetes
* Document engineering decisions throughout the project

---

## Current Status

**Sprint 4 Completed – Reverse Proxy Architecture**

### Current Features

* Flask REST API
* Health check endpoint
* Incident API
* Dockerized backend
* Docker Compose orchestration
* Nginx reverse proxy
* Automatic Docker networking
* Internal DNS-based service discovery

### Current Architecture

```text
                 Browser
                     │
                     ▼
                  Nginx
             Reverse Proxy
                     │
         Docker Compose Network
                     │
                     ▼
              Flask Backend
```

### Next Sprint

* Integrate MySQL
* Persist incident data using Docker Volumes
* Replace in-memory data with a real database

---

## Technology Stack

### Current

* Python
* Flask
* Docker
* Docker Compose
* Nginx

### Planned

* MySQL
* AWS EC2
* GitHub Actions
* Terraform
* Kubernetes

---

## Repository Structure

```text
opsboard/
│
├── backend/
│   ├── app.py
│   ├── Dockerfile
│   ├── requirements.txt
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
├── compose.yaml
├── CHANGELOG.md
└── README.md
```

---

## API Endpoints

| Method | Endpoint            | Description                |
| ------ | ------------------- | -------------------------- |
| GET    | /                   | API information            |
| GET    | /api/health         | Health check               |
| GET    | /api/incidents      | Retrieve all incidents     |
| GET    | /api/incidents/<id> | Retrieve a single incident |

---

## Development Roadmap

* [x] Build Flask REST API
* [x] Containerize backend with Docker
* [x] Orchestrate services using Docker Compose
* [x] Add Nginx reverse proxy
* [ ] Integrate MySQL database
* [ ] Add persistent Docker volumes
* [ ] Deploy to AWS EC2
* [ ] Implement CI/CD with GitHub Actions
* [ ] Provision infrastructure using Terraform
* [ ] Deploy to Kubernetes

---

## Engineering Principles

Throughout this project, the focus is not only on building software but also on applying professional engineering practices, including:

* Infrastructure as Code
* Container-first development
* Incremental architecture evolution
* Version-controlled documentation
* Conventional Git commits
* Production-inspired project structure

---

This repository documents my journey toward becoming a Cloud & DevOps Engineer by building, documenting, and deploying a production-inspired application one sprint at a time.
