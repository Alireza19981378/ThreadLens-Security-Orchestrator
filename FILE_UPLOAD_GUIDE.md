# File Upload Guide

This guide explains how Dockerfile and file uploads work in the ThreadLens frontend and backend.

## Supported Upload Flows

The UI supports two upload-oriented workflows:

- Dockerfile scanning: upload or paste a Dockerfile.
- File sandbox analysis: upload a file for malware, metadata, YARA, ClamAV, Gitleaks, and TruffleHog analysis.

The frontend sends uploads as `multipart/form-data`. The backend stores uploaded content under a safe generated filename, then scans the stored path.

## Dockerfile Upload Features

### Click To Select

Click the Dockerfile upload area to open the system file picker.

```text
Dashboard -> New Scan -> Dockerfile
Upload area -> click to select a Dockerfile
```

### Drag And Drop

Drag a Dockerfile from Finder, Explorer, or your file manager and drop it on the upload area.

### Filename Indicator

After a file is selected, the UI shows the selected filename near the Dockerfile editor.

```text
Inline Dockerfile    selected: Dockerfile
```

## How To Use Dockerfile Upload

1. Open the dashboard.
2. Go to `New Scan`.
3. Select the `Dockerfile` scan type.
4. Either paste Dockerfile content, click the upload area, or drag and drop a file.
5. Confirm that the selected filename or inline content is visible.
6. Click scan.

If a file is selected, the frontend uploads the file. If no file is selected, the inline Dockerfile text is sent as the target.

## File Sandbox Upload

1. Open the dashboard.
2. Go to `New Scan`.
3. Select the `File` scan type.
4. Choose or drop a file.
5. Click scan.

The backend checks the file size against:

```env
FILE_SANDBOX_MAX_UPLOAD_MB=50
```

The default sandbox storage directory is:

```env
FILE_SANDBOX_STORAGE_DIR=./var/file_sandbox
```

## End-To-End Upload Flow

```text
Browser
  -> User selects or drops a file
Frontend
  -> Stores the File object in React state
  -> Builds FormData
  -> Sends POST /api/mocks/dashboard/scan
Next.js API proxy
  -> Forwards request to Django
Backend
  -> Parses multipart/form-data
  -> Saves uploaded file with a safe generated name
  -> Creates ScanTask
Worker / inline task
  -> Runs applicable scanners
  -> Normalizes output
Frontend
  -> Polls status and displays results
```

## Backend Storage

Dockerfile uploads are stored under:

```text
backend/var/uploads/
```

File sandbox uploads are stored under:

```text
backend/var/file_sandbox/
```

Generated filenames include a timestamp, UUID, and sanitized original filename.

Example:

```text
20260708095520123456_4f0db4f607e54790a83ac7c5c902af7b_Dockerfile
20260708095600123456_765fa8a2d3fd4f6d8d88e87e6f01a222_sample.pdf
```

## API Endpoints

### Create Scan

```http
POST /api/v1/scans/
Content-Type: multipart/form-data
Authorization: Bearer <access-token>
```

Dockerfile upload fields:

```text
asset_type=dockerfile
target=Dockerfile
file=<binary>
options={"generate_sbom":true,"deep_scan":true}
```

File sandbox upload fields:

```text
asset_type=file
target=sample.bin
file=<binary>
options={"generate_sbom":true,"deep_scan":true}
```

Response:

```json
{
  "task_id": "uuid",
  "id": "uuid",
  "status": "PENDING",
  "progress": 0
}
```

### Legacy File Upload Endpoint

The backend also exposes:

```http
POST /api/v1/upload-file/
```

This endpoint stores a file and returns metadata, but the main dashboard flow uses `POST /api/v1/scans/`.

## Scanners Used After Upload

Dockerfile scans can run:

- Hadolint
- Checkov
- KICS
- Gitleaks
- TruffleHog

File scans can run:

- ClamAV
- YARA
- ExifTool
- pdfinfo, only for detected PDFs
- Gitleaks
- TruffleHog

Tools are skipped when:

- the scanner is disabled in admin settings
- the scanner is inactive
- the binary is missing
- the detected file type does not match the scanner

Skipped tools are reported in logs and `toolStatus`.

## Frontend Configuration

The Next.js frontend uses API proxy routes under:

```text
frontend/src/app/api/
```

The dashboard scan proxy is:

```text
frontend/src/app/api/mocks/dashboard/scan/route.ts
```

Set the backend URL with:

```env
BACKEND_API_URL=http://127.0.0.1:8000
```

In Docker Compose, the frontend uses:

```env
BACKEND_API_URL=http://backend:8000
```

## Backend Configuration

Important backend settings:

```env
MAX_UPLOAD_SIZE=104857600
FILE_SANDBOX_ENABLED=true
FILE_SANDBOX_MAX_UPLOAD_MB=50
FILE_SANDBOX_STORAGE_DIR=./var/file_sandbox
SCANNER_WORK_DIR=./var/scans
```

Docker mode uses:

```env
FILE_SANDBOX_STORAGE_DIR=/app/var/file_sandbox
SCANNER_WORK_DIR=/app/var/scans
```

## Manual Local Test

Backend:

```bash
cd backend
source .venv/bin/activate
python manage.py runserver 127.0.0.1:8000
```

Frontend:

```bash
cd frontend
npm run dev
```

Browser:

1. Open `http://localhost:3000`.
2. Log in.
3. Go to `New Scan`.
4. Select Dockerfile or File mode.
5. Upload a test file.
6. Start the scan.
7. Open the result tabs and check logs/tool status.

## cURL Test

Create a scan with a Dockerfile upload:

```bash
curl -X POST \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "asset_type=dockerfile" \
  -F "target=Dockerfile" \
  -F "file=@./Dockerfile" \
  -F 'options={"generate_sbom":true,"deep_scan":true}' \
  http://127.0.0.1:8000/api/v1/scans/
```

Create a file sandbox scan:

```bash
curl -X POST \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "asset_type=file" \
  -F "target=sample.pdf" \
  -F "file=@./sample.pdf" \
  -F 'options={"generate_sbom":true,"deep_scan":true}' \
  http://127.0.0.1:8000/api/v1/scans/
```

## Troubleshooting

### File Picker Does Not Open

Check the browser console and confirm:

- the upload area click handler is running
- the hidden file input exists
- no overlay is blocking the upload area

### Drag And Drop Does Not Work

Check that the browser receives drag events:

- `dragover`
- `dragleave`
- `drop`

Also confirm the file is not blocked by browser security or an unsupported path.

### Upload Fails

Check:

```bash
cd backend
source .venv/bin/activate
python manage.py runserver
```

Then inspect:

- backend terminal logs
- frontend browser console
- Network tab response body
- authentication token
- max upload size

### Backend Returns HTML Instead Of JSON

This usually means Django raised an unhandled error. Check the backend terminal logs. The frontend proxy converts HTML errors into a short message, but the full traceback is in the backend logs when `DJANGO_DEBUG=true`.

### File Is Uploaded But Scanner Has No Results

Open the `Errors & Logs` or `toolStatus` view and check whether scanners were:

- successful with zero findings
- skipped because the binary was missing
- skipped because the file type did not match
- disabled or inactive in the admin panel

### pdfinfo Does Not Run

`pdfinfo` runs only for files detected as PDFs. Install Poppler if needed:

```bash
brew install poppler
sudo apt-get install poppler-utils
```

### Secret Scanner Has No Findings

Gitleaks and TruffleHog use real detection rules. Fake secrets may not trigger both tools. Use the built-in secret leak Dockerfile sample to test Gitleaks output.

## Notes For Production

- Treat all uploaded files as untrusted.
- Do not store uploads outside the configured scan/sandbox directories.
- Keep scanner containers or workers isolated from the host when possible.
- Keep ClamAV and YARA rules updated.
- Use the Admin Tool Management page to disable tools that are not installed.
