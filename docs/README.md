# ThreadLens Technical Documentation

## Project Overview

ThreadLens is a multi-scanner analysis platform for container images, Dockerfiles, Git repositories, and uploaded files. It coordinates external security tools, captures progressive scan state, normalizes raw scanner output, calculates risk scores, and exposes the results through a Next.js dashboard.

The application solves a common operational problem: each security scanner has its own CLI, output format, update flow, and failure mode. This project gives those scanners a single API and UI while keeping each tool optional and independently manageable.

Main modules:

- Backend API: Django REST Framework service under `backend/`.
- Worker orchestration: Celery tasks run scans and update jobs.
- Frontend UI: Next.js dashboard under `frontend/`.
- Database: PostgreSQL in Docker, SQLite by default for local development.
- Queue: Redis for Celery worker and scheduled update crawler.
- Tool logs: JSON logs to files/stdout and optional Elasticsearch.
- Scanner registry: persistent scanner config and tool state in the database.

## Architecture

### Backend

The backend is a Django REST Framework application. Important paths:

- `backend/config/settings.py`: environment-driven runtime settings.
- `backend/scanner_engine/models.py`: scan tasks, scanner config, tool state, YARA rules.
- `backend/scanner_engine/views.py`: API endpoints for scans, admin tools, users, auth helper routes.
- `backend/scanner_engine/tasks.py`: Celery task entrypoints.
- `backend/scanner_engine/core/orchestrator.py`: scan routing, execution, logging, and error handling.
- `backend/scanner_engine/core/scanners/command_scanners.py`: concrete scanner adapters.
- `backend/scanner_engine/core/normalizers.py`: converts raw scanner output into UI/API schemas.
- `backend/scanner_engine/core/tool_updates.py`: version checks, DB/signature updates, binary update actions.

The backend stores scan state in `ScanTask`. The frontend polls scan status and result endpoints. Each external command execution is logged with command, exit code, stdout/stderr, duration, and audit metadata.

### Frontend

The frontend is a Next.js application:

- `frontend/src/app/login`: login page.
- `frontend/src/app/(dashboard)/dashboard/page.tsx`: scan creation, progress, results tabs.
- `frontend/src/app/admin/page.tsx`: tool management and user management.
- `frontend/src/app/api/*`: Next.js proxy routes to the Django API.
- `frontend/src/lib/auth.ts`: JWT token storage and auth headers.
- `frontend/src/lib/mock-data.ts`: UI data types and fallback/demo data.

The UI shows:

- scan history and active scan progress
- tool status and logs
- CVEs and severity counts
- secret findings
- Dockerfile/IaC misconfigurations
- malware/YARA/ClamAV results
- metadata from ExifTool and pdfinfo
- SBOM/license inventory
- unified risk score and verdict

### Queue And Workers

Local development can run scans inline with:

```env
SCANNER_RUN_INLINE=true
```

Docker mode uses Celery:

- `backend`: API server
- `worker`: executes scan and update tasks
- `beat`: runs periodic crawler checks
- `redis`: Celery broker/result backend

The worker uses shared locks for scans and exclusive locks for update operations so update jobs do not corrupt scanner state while scans are active.

### Database

Local default is SQLite:

```env
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=backend/db.sqlite3
```

Docker default is PostgreSQL:

```env
DB_ENGINE=django.db.backends.postgresql
DB_HOST=postgres
DB_NAME=multiav
```

Persistent data includes:

- scan tasks and normalized results
- scanner enable/disable settings
- tool state, versions, last errors, and logs
- users and roles
- YARA rule records

### Scanner Engines

The scanner registry lives in `backend/scanner_engine/core/registry.py`. It maps a tool name to:

- display name
- category
- supported input types
- executable path
- scanner adapter class

Scanner settings are persisted in `ScannerConfig`, and runtime health is stored in `ToolState`.

### Rule And Database Update Jobs

The admin UI supports separate actions:

- check installed tool version
- check database/signature version
- update binary/tool, only if a command is configured
- update database/signatures, where supported

Database/signature updates:

- ClamAV: `freshclam`
- YARA: downloads configured Git rule repositories into `YARA_RULES_DIR`
- Grype: `grype db update`
- Trivy: `trivy image --download-db-only`

Binary updates are intentionally not guessed. Configure them with env vars such as:

```env
TRIVY_UPDATE_COMMAND="brew upgrade aquasecurity/trivy/trivy"
GRYPE_UPDATE_COMMAND="brew upgrade grype"
CLAMAV_UPDATE_COMMAND="brew upgrade clamav"
```

## End-To-End Scan Flow

1. User logs in and creates a scan from the frontend.
2. Frontend sends `POST /api/v1/scans/` through the Next.js proxy.
3. Backend validates `input_type` and stores uploaded files with safe generated filenames.
4. File analysis computes a file profile: MIME/magic type, extension, PDF suspicious tags, and mismatch flags.
5. Image scans optionally generate Syft SBOMs and CycloneDX SBOMs.
6. Image deep scans optionally export the container filesystem for filesystem scanners.
7. The orchestrator loads enabled and active scanners from the registry.
8. Type-specific routing skips tools that do not apply. Example: `pdfinfo` only runs for PDFs.
9. Missing binaries are recorded as `missing_binary` or `skipped`, not fatal scan crashes.
10. Each scanner runs through a tool adapter and logs structured execution data.
11. Raw results are persisted as scanners complete.
12. Normalizers convert raw results into common buckets: CVEs, secrets, misconfigs, malware, metadata, SBOM.
13. Scoring computes malware/file score and overall scan score.
14. Frontend polls status, shows live pipeline progress, then displays result tabs.

## Scanner Tools

### ClamAV

- Purpose: malware signature scanning.
- Inputs: exported image filesystem or uploaded file.
- Command: `clamscan`.
- Output: text summary and match lines.
- Parser: extracts `FOUND` lines into malware alerts.
- Updates: `freshclam`.
- Optional: yes. Missing binary is shown as skipped/missing.

### YARA

- Purpose: static malware/signature matching.
- Inputs: exported image filesystem, Git checkout, or uploaded file.
- Command: `yara -w -r <rules> <target>`.
- Output: text match lines.
- Parser: match lines become malware findings.
- Updates: Git rule repositories in `YARA_RULES_DIR`.
- Optional: yes. Missing rules produce a clear skipped/error state.

### ExifTool

- Purpose: metadata extraction.
- Inputs: uploaded files.
- Command: `exiftool -json <file>`.
- Output: JSON list.
- Parser: first metadata object is shown in the Metadata tab.
- Optional: yes.

### pdfinfo / Poppler

- Purpose: PDF metadata, JavaScript/action hints, structure.
- Inputs: only files detected as `application/pdf`.
- Command: `pdfinfo -meta -js -struct <file>`.
- Output: text key/value lines.
- Parser: converts lines into metadata map.
- Optional: yes. Non-PDF files skip this scanner.

### Gitleaks

- Purpose: secrets and credential leakage detection.
- Inputs: Git repositories, Dockerfiles, uploaded files, exported filesystems.
- Command for files: `gitleaks detect --no-git --source <file> --report-format json --report-path <tmp> --redact`.
- Output: JSON array.
- Parser: emits entries in `secrets`.
- Optional: yes.

### TruffleHog

- Purpose: secret detection with detector-based verification support.
- Inputs: filesystem paths/files.
- Command: `trufflehog filesystem <target> --json --no-update --no-verification`.
- Output: JSON lines.
- Parser: filters real finding events and ignores TruffleHog progress log events.
- Optional: yes. Fake samples may produce zero findings; UI shows tool status.

### Trivy

- Purpose: container image vulnerability scanning.
- Inputs: image reference.
- Command: `trivy image --format json --quiet --skip-java-db-update <image>`.
- Output: JSON.
- Parser: extracts vulnerabilities into CVE rows.
- Updates: `trivy image --download-db-only`.
- Optional: yes.

### Grype

- Purpose: container image vulnerability scanning.
- Inputs: image reference.
- Command: `grype <image> -o json`.
- Output: JSON.
- Parser: extracts matches into CVE rows.
- Updates: `grype db update`.
- Optional: yes.

### OSV-Scanner

- Purpose: vulnerability lookup from SBOM.
- Inputs: CycloneDX SBOM generated by Syft.
- Command: `osv-scanner -L sbom.cdx.json --format json`.
- Output: JSON.
- Parser: extracts package vulnerabilities and warnings.
- Optional: yes.

### Syft

- Purpose: SBOM generation.
- Inputs: image reference.
- Output: Syft JSON and CycloneDX JSON.
- Parser: SBOM inventory and OSV input.
- Optional for image scans, but OSV depends on CycloneDX output.

### Grant

- Purpose: license/SBOM inventory scanner.
- Inputs: image reference.
- Command: `grant list <image> -o json`.
- Output: JSON.
- Parser: normalized into SBOM/license inventory.
- Optional: yes.

### Hadolint

- Purpose: Dockerfile lint and best-practice checks.
- Inputs: Dockerfile.
- Command: `hadolint -f json <Dockerfile>`.
- Output: JSON list.
- Parser: normalized into misconfiguration findings.
- Optional: yes. Exit code `1` means findings, not command failure.

### Checkov

- Purpose: IaC and Dockerfile policy scanning.
- Inputs: Dockerfile or Git repository.
- Command: `checkov -f <file> -o json --quiet` or directory mode.
- Output: JSON.
- Parser: failed checks become misconfigurations.
- Optional: yes.

### KICS

- Purpose: IaC and Dockerfile policy scanning.
- Inputs: Dockerfile or Git repository.
- Command: `kics scan -p <target> -q <queries> --report-formats json`.
- Output: JSON report file.
- Parser: query/file results become misconfigurations.
- Optional: yes. Requires a valid queries directory.

### Clair And Anchore

- Purpose: additional image vulnerability scanners if binaries are available.
- Inputs: image reference.
- Output: JSON.
- Parser: vulnerability lists become CVE rows.
- Optional: yes.

## Scoring And Verdicts

File malware score:

- ClamAV detection sets score to 95 or higher.
- YARA high-severity matches add 25 points each, capped.
- Suspicious PDF tags such as `/JavaScript` or `/Launch` add risk.
- Gitleaks/TruffleHog secrets add risk.
- Metadata anomalies such as extension/magic mismatch add risk.

Overall scan score:

- Critical CVEs heavily increase score.
- High CVEs increase score.
- Secrets and misconfigurations add additional risk.

Verdict ranges:

- `Clean`: 0-10
- `Suspicious`: 11-50
- `Malicious`: 51-85
- `High Risk`: 86-100

## API Summary

Authentication:

- `POST /api/v1/auth/login/`
- `POST /api/v1/auth/refresh/`
- `POST /api/v1/auth/logout/`
- `GET /api/v1/auth/me/`

Dashboard and scans:

- `GET /api/v1/dashboard/`
- `POST /api/v1/scans/`
- `GET /api/v1/scans/<task_id>/status/`
- `GET /api/v1/scans/<task_id>/results/`
- `POST /api/v1/upload-file/`

Admin:

- `GET/POST /api/v1/admin/tools/`
- `PATCH/DELETE /api/v1/admin/tools/<tool_name>/`
- `POST /api/v1/admin/tools/<tool_name>/actions/`
- `POST /api/v1/admin/tools/crawler/`
- `PUT /api/v1/admin/config/`
- `GET/POST /api/v1/admin/users/`
- `PATCH/DELETE /api/v1/admin/users/<id>/`
- `POST /api/v1/admin/yara-rules/`

Scan result shape:

```json
{
  "task": {"id": "...", "status": "SUCCESS", "progress": 100, "logs": []},
  "metadata": {},
  "cves": [],
  "secrets": [],
  "misconfigurations": [],
  "malware": [],
  "malwareScore": {},
  "scanScore": {},
  "sbom": [],
  "errors": [],
  "toolStatus": [],
  "raw_results": {},
  "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0}
}
```

## JSON Logging And ELK

The backend writes one JSON object per log line to:

```text
backend/var/logs/app.log
```

The path can be changed with:

```env
LOG_FILE_PATH=/app/var/logs/app.log
```

Log rotation is enabled with `RotatingFileHandler`:

- max file size: `10 MB`
- retained backups: `5`

Each log event uses a stable ELK-friendly schema:

```json
{
  "timestamp": "2026-07-08T10:00:00+00:00",
  "log_level": "INFO",
  "module": "orchestrator",
  "logger": "scanner_engine.scan",
  "message": "Running clamav against sample.pdf.",
  "task_id": "scan-uuid",
  "scanner_name": "clamav",
  "metadata": {
    "target": "sample.pdf",
    "progress": 40,
    "source_file": "/app/scanner_engine/core/orchestrator.py",
    "line_number": 31
  }
}
```

Scanner execution logs include nested metadata for command execution:

```json
{
  "timestamp": "2026-07-08T10:00:00+00:00",
  "log_level": "INFO",
  "module": "scanner_execution",
  "message": "security tool execution",
  "task_id": "scan-uuid",
  "scanner_name": "gitleaks",
  "metadata": {
    "target_file": {},
    "scanner": {},
    "execution": {},
    "audit": {}
  }
}
```

Logstash template:

```text
elastic/logstash-security-logs.conf
```

It uses `codec => json` and writes to:

```text
security-logs-%{+YYYY.MM.dd}
```

## Local Development

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_scanners
python manage.py runserver 127.0.0.1:8000
```

Frontend:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Worker mode locally:

```bash
redis-server
cd backend
source .venv/bin/activate
export SCANNER_RUN_INLINE=false
celery -A config worker -l info
celery -A config beat -l info
```

Bootstrap host tools:

```bash
./scripts/bootstrap_tools.sh
```

For a faster bootstrap that skips DB/rule downloads:

```bash
BOOTSTRAP_UPDATE_CLAMAV=false BOOTSTRAP_YARA_RULES=false ./scripts/bootstrap_tools.sh
```

## Docker Run

Create environment file:

```bash
cp .env.example .env
```

Build and start:

```bash
docker compose up --build
```

Open:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- Elasticsearch: `http://localhost:9200`

Run migrations/commands manually:

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_scanners
docker compose exec backend python manage.py createsuperuser
```

Update scanner databases:

```bash
docker compose exec backend freshclam
docker compose exec backend python manage.py seed_yara_rules
docker compose exec backend grype db update
docker compose exec backend trivy image --download-db-only
```

Persistent Docker volumes:

- `postgres_data`: database
- `redis_data`: Redis append-only data
- `elasticsearch_data`: Elasticsearch index data
- `scanner_var`: uploads, scan workspaces, logs, YARA rules
- `clamav_db`: ClamAV signatures

## Environment Variables

Core:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `CORS_ALLOWED_ORIGINS`
- `SCANNER_RUN_INLINE`
- `SCANNER_MOCK_MODE`
- `SCANNER_WORK_DIR`
- `TOOL_LOCK_DIR`
- `MAX_UPLOAD_SIZE`

Database/queue:

- `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`

File sandbox:

- `FILE_SANDBOX_ENABLED`
- `FILE_SANDBOX_MAX_UPLOAD_MB`
- `FILE_SANDBOX_STORAGE_DIR`

Tools:

- `CLAMAV_ENABLED`, `CLAMSCAN_BIN`, `FRESHCLAM_BIN`
- `YARA_ENABLED`, `YARA_BIN`, `YARA_RULES_DIR`, `YARA_RULE_REPOS`
- `EXIFTOOL_ENABLED`, `EXIFTOOL_BIN`
- `PDFINFO_ENABLED`, `PDFINFO_BIN`

Logging:

- `ELASTICSEARCH_ENABLED`
- `ELASTICSEARCH_URL`
- `ELASTICSEARCH_INDEX`
- `LOG_FILE_PATH`

Optional binary update commands:

- `CLAMAV_UPDATE_COMMAND`
- `TRIVY_UPDATE_COMMAND`
- `GRYPE_UPDATE_COMMAND`
- `GRANT_UPDATE_COMMAND`
- `OSV_SCANNER_UPDATE_COMMAND`

## Security And Hardening

The Docker Compose setup uses:

- non-root users inside application containers
- `cap_drop: ["ALL"]`
- `security_opt: ["no-new-privileges:true"]`
- read-only root filesystems for app containers
- tmpfs for `/tmp`
- persistent writable volumes only where needed

Uploaded files and extracted filesystems are untrusted. Do not mount the Docker socket into the worker unless you accept the host escape risk. For image filesystem export in a hardened deployment, prefer an isolated scanner host or a dedicated sandbox VM.

## Troubleshooting

### `Executable not found: pdfinfo`

Install Poppler:

```bash
brew install poppler
sudo apt-get install poppler-utils
```

If Django runs with a different `PATH`, set an absolute path:

```env
PDFINFO_BIN=/opt/homebrew/bin/pdfinfo
```

Then run:

```bash
python manage.py seed_scanners
```

### ExifTool version check says `File not found - version`

Use the current code path. ExifTool version checks must run `exiftool -ver`, not `exiftool version`.

### ClamAV database is stale or missing

Run:

```bash
freshclam
```

In Docker:

```bash
docker compose exec backend freshclam
```

If permissions fail, check the `clamav_db` volume and ownership.

### YARA has no results

Check:

```bash
ls backend/var/yara_rules
python manage.py seed_yara_rules
```

YARA warnings are suppressed with `-w`; warnings should not fail the scan.

### KICS cannot find queries

Set `ScannerConfig.local_db_path` or `KICS_QUERIES_PATH` to the KICS `assets/queries` directory. Rerun `python manage.py seed_scanners` after installing KICS.

### Gitleaks or TruffleHog returns no findings

Confirm the tool ran in the `Errors & Logs` or `Secret & Credential Leaks` tab. Fake credentials are often ignored. Gitleaks sample findings are included in the Dockerfile sample. TruffleHog may report zero findings for fake secrets.

### Trivy Java DB download fails

The app runs Trivy with `--skip-java-db-update`. If the vulnerability DB is missing, run:

```bash
trivy image --download-db-only
```

Check DNS/network access from the worker container.

### Scanner skipped because binary is missing

Install the binary with:

```bash
./scripts/bootstrap_tools.sh
```

Or disable the scanner from the Admin Tool Management page.

## Recommended Production Steps

1. Set a strong `DJANGO_SECRET_KEY`.
2. Set `DJANGO_DEBUG=false`.
3. Use PostgreSQL, Redis, and Elasticsearch managed or hardened services.
4. Keep scanner databases updated with scheduled jobs.
5. Run image/filesystem scanning in an isolated host or VM if Docker access is required.
6. Review tool logs in Elasticsearch.
7. Keep binary update commands explicit and reviewed.
