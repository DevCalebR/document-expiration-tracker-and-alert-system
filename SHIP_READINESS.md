# Ship Readiness

## Completed
- Fixed nested object-key deletion end to end, including frontend encoding and backend path routing.
- Made backend tests pass by default with SQLite, fakeredis, and deterministic test setup.
- Hardened logging so non-request log records always include a safe `request_id`.
- Switched the frontend to async processing with job polling, timeout handling, retry, and sync fallback.
- Added end-to-end cloud OAuth routes and UI flows for Google Drive, Dropbox, and OneDrive.
- Corrected SMTP-disabled behavior so registration and admin test email responses are accurate.
- Added admin UI for system status, alert runs, and test email.
- Promoted a first-class all-local developer profile with SQLite, filesystem storage, fakeredis, and eager jobs.
- Updated docs, env examples, and local launcher behavior.

## Commands Run
```bash
cd /Users/caleb/Desktop/DocExpire/backend
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

```bash
cd /Users/caleb/Desktop/DocExpire/frontend
npm test -- --run
npm run build
```

```bash
cd /Users/caleb/Desktop/DocExpire/backend
APP_ENV=development \
APP_DEBUG=False \
APP_SECRET_KEY=local-smoke-app-secret-key-change-1234 \
JWT_SECRET_KEY=local-smoke-jwt-secret-key-change-1234 \
DATABASE_URL=sqlite:///./smoke.db \
REDIS_URL=fakeredis:// \
RQ_ASYNC=False \
STORAGE_PROVIDER=filesystem \
STORAGE_FILESYSTEM_ROOT=./smoke-uploads \
FRONTEND_URL=http://localhost:5173 \
CORS_ALLOW_ORIGINS=http://localhost:5173 \
ALLOWED_HOSTS=localhost,127.0.0.1 \
alembic upgrade head
```

```bash
cd /Users/caleb/Desktop/DocExpire/backend
APP_ENV=development \
APP_DEBUG=False \
APP_SECRET_KEY=local-smoke-app-secret-key-change-1234 \
JWT_SECRET_KEY=local-smoke-jwt-secret-key-change-1234 \
DATABASE_URL=sqlite:///./smoke.db \
REDIS_URL=fakeredis:// \
RQ_ASYNC=False \
STORAGE_PROVIDER=filesystem \
STORAGE_FILESYSTEM_ROOT=./smoke-uploads \
FRONTEND_URL=http://localhost:5173 \
CORS_ALLOW_ORIGINS=http://localhost:5173 \
ALLOWED_HOSTS=localhost,127.0.0.1 \
uvicorn main:app --host 127.0.0.1 --port 8010
```

```bash
cd /Users/caleb/Desktop/DocExpire/backend
APP_ENV=development APP_SECRET_KEY=local-worker-app-secret-key-change-1234 JWT_SECRET_KEY=local-worker-jwt-secret-key-change-1234 DATABASE_URL=sqlite:///./worker-smoke.db REDIS_URL=fakeredis:// RQ_ASYNC=False STORAGE_PROVIDER=filesystem STORAGE_FILESYSTEM_ROOT=./worker-smoke-uploads FRONTEND_URL=http://localhost:5173 ALLOWED_HOSTS=localhost,127.0.0.1 CORS_ALLOW_ORIGINS=http://localhost:5173 python worker.py
```

```bash
cd /Users/caleb/Desktop/DocExpire/backend
APP_ENV=development APP_SECRET_KEY=local-scheduler-app-secret-key-1234 JWT_SECRET_KEY=local-scheduler-jwt-secret-key-1234 DATABASE_URL=sqlite:///./scheduler-smoke.db REDIS_URL=fakeredis:// RQ_ASYNC=False STORAGE_PROVIDER=filesystem STORAGE_FILESYSTEM_ROOT=./scheduler-smoke-uploads FRONTEND_URL=http://localhost:5173 ALLOWED_HOSTS=localhost,127.0.0.1 CORS_ALLOW_ORIGINS=http://localhost:5173 python - <<'PY'
from scheduler import enqueue_alerts
enqueue_alerts()
print('scheduler_enqueue_ok')
PY
```

## Passed
- Backend test suite: `10 passed, 2 warnings`
- Frontend test suite: `4 passed`
- Frontend production build: succeeded
- Local HTTP smoke: `healthz`, `readyz`, `register`, `verify`, `login`, `auth/me`, `cloud/providers`, `upload`, `process/async`, `jobs/{id}`, `extract-text`, `expiring-soon`, `delete`, `list files`
- Local worker behavior: exits cleanly in eager mode with `worker_not_required_in_eager_mode`
- Scheduler helper: enqueue path executed successfully in local mode

## Remaining Non-Blocking Limitations
- Live Google Drive / Dropbox / OneDrive vendor handshakes still require real provider credentials to exercise against external APIs.
- AI insights require `ANTHROPIC_API_KEY` to return real model-backed analysis.
- OCR quality and PDF extraction still depend on local `tesseract` and `pdftoppm` installations.
