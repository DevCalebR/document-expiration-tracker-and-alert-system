# DocExpire

DocExpire tracks uploaded and cloud-imported documents, extracts expiration dates with OCR, shows expiring-soon risk in the UI, and can send scheduled alert emails.

## What ships in this repo
- `backend/`: FastAPI API, OCR/date extraction, queue jobs, alert scheduler, OAuth callbacks, storage adapters
- `frontend/`: React/Vite UI for auth, uploads, async processing, cloud import, reporting, and admin ops
- `run.sh`: macOS convenience launcher for local API + frontend

## Features
- JWT auth with registration, email verification, login/logout, and admin role gating
- Upload support for PDF, PNG, JPG, and JPEG
- OCR and date extraction with persisted document/date records
- Async background processing with job polling in the UI and sync fallback when needed
- Expiring-soon reporting, CSV export, AI analysis, and audit logs
- Google Drive, Dropbox, and OneDrive OAuth connect/import flows
- Admin operations panel for system status, alert runs, and SMTP test email
- Local-first runtime profile: SQLite, filesystem storage, fakeredis, eager jobs

## Prerequisites
### Backend runtime
- Python 3.11+
- Tesseract OCR
- Poppler (`pdftoppm`) for PDF image extraction

### macOS
```bash
brew install tesseract poppler
```

### Ubuntu / Debian
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr poppler-utils
```

## Quick start: all-local mode
This is the default developer profile. It does not require Postgres, S3, or Redis.

### 1. Backend
```bash
cd /Users/caleb/Desktop/DocExpire/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
uvicorn main:app --reload
```

Local defaults after copying `backend/.env.example`:
- SQLite database at `backend/docexpire.db`
- Filesystem object storage at `backend/local_storage`
- fakeredis queue backend with eager execution (`RQ_ASYNC=False`)
- Manual verification links when SMTP is not configured

### 2. Frontend
```bash
cd /Users/caleb/Desktop/DocExpire/frontend
npm install
cp .env.example .env
npm run dev
```

The UI runs at [http://localhost:5173](http://localhost:5173) and points to [http://127.0.0.1:8000](http://127.0.0.1:8000) by default.

### 3. Convenience launcher (macOS)
```bash
cd /Users/caleb/Desktop/DocExpire
./run.sh
```

`run.sh` starts only the API and frontend because local mode uses eager background jobs. A separate worker is not required unless you enable `RQ_ASYNC=True`.

## Background jobs and alerts
### Worker
Only required when `RQ_ASYNC=True`.
```bash
cd /Users/caleb/Desktop/DocExpire/backend
source .venv/bin/activate
python worker.py
```

### Scheduler
Required when you want periodic alert enqueueing.
```bash
cd /Users/caleb/Desktop/DocExpire/backend
source .venv/bin/activate
python scheduler.py
```

## Tests and validation
### Backend tests
```bash
cd /Users/caleb/Desktop/DocExpire/backend
source .venv/bin/activate
pytest -q
```

### Frontend tests
```bash
cd /Users/caleb/Desktop/DocExpire/frontend
npm test -- --run
```

### Frontend production build
```bash
cd /Users/caleb/Desktop/DocExpire/frontend
npm run build
```

## Cloud OAuth setup
Cloud import is disabled in the UI until backend credentials are configured.

### Google Drive
Set:
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI`

Recommended local callback:
- `http://127.0.0.1:8000/cloud/google_drive/callback`

### Dropbox
Set:
- `DROPBOX_APP_KEY`
- `DROPBOX_APP_SECRET`
- `DROPBOX_REDIRECT_URI`

Recommended local callback:
- `http://127.0.0.1:8000/cloud/dropbox/callback`

### OneDrive
Set:
- `MICROSOFT_CLIENT_ID`
- `MICROSOFT_CLIENT_SECRET`
- `MICROSOFT_REDIRECT_URI`
- `MICROSOFT_TENANT_ID` (usually `common`)

Recommended local callback:
- `http://127.0.0.1:8000/cloud/onedrive/callback`

Tokens are stored in the existing database and encrypted at rest. In staging and production you must set `TOKEN_ENCRYPTION_KEY`.

## SMTP behavior
SMTP is optional in development and test.
- If SMTP is configured, registration sends verification emails and the admin panel can send test mail.
- If SMTP is not configured, local registration succeeds but returns a manual verification link instead of claiming email was sent.
- In staging and production, registration is blocked until SMTP is configured.

## Production requirements
Production needs explicit infrastructure and secrets. At minimum set:
- `APP_ENV=production`
- `APP_SECRET_KEY`
- `JWT_SECRET_KEY`
- `TOKEN_ENCRYPTION_KEY`
- `DATABASE_URL` to Postgres or another production-grade database
- `REDIS_URL` to a real Redis instance
- `RQ_ASYNC=True`
- `STORAGE_PROVIDER` and corresponding object storage credentials
- `ALLOWED_HOSTS`
- `CORS_ALLOW_ORIGINS`
- `SMTP_*` and `FROM_EMAIL`
- `SECURE_HEADERS_HSTS_SECONDS` to a non-zero value behind HTTPS

Recommended production processes:
- API: `uvicorn` behind a reverse proxy or process manager
- Worker: `python worker.py`
- Scheduler: `python scheduler.py`
- External services: managed Postgres, Redis, and object storage

## Health and ops endpoints
- `GET /healthz`: liveness
- `GET /readyz`: readiness with DB and Redis dependency status
- `GET /admin/status`: admin-only ops summary including queue mode and email/cloud config
- `POST /admin/alerts/run`: admin-only manual alert enqueue
- `POST /admin/test-email`: admin-only SMTP validation

## Notes
- The frontend now processes documents through the async queue endpoint first and polls job state until completion.
- The delete route accepts nested storage keys, so keys like `uploads/<user>/<file>` are safe.
- Filesystem storage and SQLite artifacts are ignored in `.gitignore` for local use.
- See [SHIP_READINESS.md](/Users/caleb/Desktop/DocExpire/SHIP_READINESS.md) for the current validation summary.
