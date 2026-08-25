# ThreadLens Backend

Django REST Framework backend for the Next.js dashboard.

## Quick start

```bash
cd /Users/arash/Documents/pro/security_orchestrator/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_scanners
python manage.py runserver 0.0.0.0:8000
```

The default configuration uses `SCANNER_MOCK_MODE=false` and `SCANNER_RUN_INLINE=true`.
In local inline mode the API creates a task immediately and runs the scan in a background
thread so the UI can poll `status/` for progressive updates. If a scanner binary is missing,
the task logs and results include the tool name plus an install hint instead of returning
fake findings. For asynchronous execution, set `SCANNER_RUN_INLINE=false`, start Redis,
and run:

```bash
celery -A config worker -l info
```

For a UI-only demo with deterministic fake findings, set `SCANNER_MOCK_MODE=true` and
restart Django. Do not use that mode for validation.

## Static file sandbox

Uploaded malware-analysis files are stored separately from generic uploads when
`FILE_SANDBOX_ENABLED=true`:

```env
FILE_SANDBOX_ENABLED=true
FILE_SANDBOX_MAX_UPLOAD_MB=50
FILE_SANDBOX_STORAGE_DIR=./var/file_sandbox
```

The backend never installs scanner binaries while handling a request. Configure paths to
pre-installed tools through env vars, then run `python manage.py seed_scanners`:

```env
CLAMAV_ENABLED=true
CLAMSCAN_BIN=clamscan
YARA_ENABLED=true
YARA_BIN=yara
YARA_RULES_DIR=./var/yara_rules
EXIFTOOL_ENABLED=true
EXIFTOOL_BIN=exiftool
PDFINFO_ENABLED=true
PDFINFO_BIN=pdfinfo
```

If a binary is missing, that scanner is marked `missing_binary` or `skipped`; the rest of
the scan continues and the UI shows the tool status.

## Frontend endpoints

- `GET /api/v1/dashboard/`
- `POST /api/v1/scans/`
- `GET /api/v1/scans/<task_id>/status/`
- `GET /api/v1/scans/<task_id>/results/`
- `GET /api/v1/tools/`
- `POST /api/v1/auth/login/`
- `POST /api/v1/auth/refresh/`
- `GET /api/v1/auth/me/`
- `GET/POST /api/v1/admin/users/`

All scan and admin APIs require JWT or session authentication. Tool configuration, YARA
rule uploads, and user management require `is_staff`, superuser, or the `security-admin`
group.

## YARA rules

Rules can be loaded in either of these ways:

```bash
python manage.py seed_yara_rules
```

The command recursively loads `*.yar`, `*.yara`, and `*.rules` from `YARA_RULES_DIR`
(default: `backend/var/yara_rules`) and updates the YARA scanner config.

Or upload a rule as an admin:

```bash
curl -H "Authorization: Bearer <token>" \
  -F "name=custom-rule" \
  -F "file=@/path/to/rule.yar" \
  http://localhost:8000/api/v1/admin/yara-rules/
```

## Docker Compose

From the repository root:

```bash
cp .env.example .env
docker compose up --build
```

Then create a superuser:

```bash
docker compose exec backend python manage.py createsuperuser
```

The compose stack runs Postgres, Redis, Elasticsearch, backend, worker, and frontend.
Services drop Linux capabilities and use `no-new-privileges`. Scanner workspaces and
uploads are stored in the `scanner_var` volume. Host Docker socket access is not mounted
by default because it weakens isolation; image scanners that require Docker should be run
in a dedicated hardened worker profile or replaced with daemonless tooling.

## Adding a scanner

1. Add a `BaseScanner` subclass in `scanner_engine/core/scanners/`.
2. Register it in `scanner_engine/core/registry.py`.
3. Run `python manage.py seed_scanners` or create/update the tool through admin/API.
