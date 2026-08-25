# ThreadLens Upgrade Plan

## Current Architecture

- Backend: Django + Django REST Framework, entrypoint `backend/manage.py`, API routes in `scanner_engine/urls.py`.
- Frontend: Next.js app router, entrypoint `frontend/src/app/(dashboard)/dashboard/page.tsx`.
- Database: Django ORM, currently SQLite by default with configurable `DB_ENGINE`/`DB_NAME`.
- Worker/orchestration: Celery task `scanner_engine.tasks.process_scan_task`; local dev can run inline.
- Scanners: command wrappers under `scanner_engine/core/scanners`, orchestrated by `scanner_engine/core/orchestrator.py`.
- Upload/state model: `ScanTask` stores target, status, progress, logs, raw results, normalized results and summary.
- Existing admin: Django admin models for scan tasks, scanner configs and YARA rules.
- Existing auth: Django auth app exists, API endpoints were not protected yet.
- Docker/Compose: no production Dockerfiles or compose stack were present at inspection time.

## Implementation Steps

1. Add authentication, token login, user profile endpoint and DRF permission defaults.
2. Add role-based permissions for admin-only scanner configuration/YARA rule management.
3. Keep scanner execution asynchronous in local mode so the UI can poll progressive status.
4. Harden upload handling: size limits, safe filenames, isolated upload directories and untrusted-file assumptions.
5. Fix Dockerfile scanner orchestration by converting inline Dockerfile content to workspace files and running Checkov/KICS/Hadolint on the right path.
6. Improve external-tool error handling with structured command metadata and partial tool results.
7. Add structured JSON logging with optional Elasticsearch handler.
8. Dockerize backend/frontend/worker and provide a hardened `docker-compose.yml`.
9. Add focused backend API/scanner tests and frontend build/lint verification.
10. Document YARA rule loading and runtime hardening expectations.
