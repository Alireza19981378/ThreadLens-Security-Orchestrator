# ThreadLens - Security Analysis Orchestration Platform

ThreadLens is a modular cybersecurity platform for automated multi-layer security analysis of:

- Container images
- Dockerfiles
- Git repositories
- Uploaded artifacts

## Research & Engineering Focus

This project explores practical security automation by integrating:

- Container security analysis
- Static security scanning
- Malware/file analysis
- Security orchestration workflows
- AI-assisted security enhancement opportunities

## Architecture

```
Frontend (Next.js)
        |
Backend API (Django + DRF)
        |
Security Orchestration Layer
        |
+---------+---------+---------+
|         |         |         |
YARA   Trivy     Grype    ClamAV
        |
Logging / Monitoring Layer
```

## Main Technologies

- Python / Django REST Framework
- Next.js
- Docker & Docker Compose
- PostgreSQL
- Elasticsearch
- Security scanning tools

## Running Locally

```bash
cp .env.example .env
docker compose up --build
```

## Repository Structure

```
backend/       Backend API and orchestration logic
frontend/      Web interface
scripts/       Setup utilities
docs/          Technical documentation
```

## Author

Alireza Sajadi

Research interests: Cybersecurity, Secure Systems, AI-assisted Security, Network Security
