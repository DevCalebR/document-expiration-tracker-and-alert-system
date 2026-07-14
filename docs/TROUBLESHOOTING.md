# Troubleshooting

## OCR executable not found

Install Tesseract and Poppler, then confirm `tesseract --version` and `pdftoppm -v` work in the same shell that starts Uvicorn.

## Frontend cannot reach the API

Confirm the API binds to `127.0.0.1:8000`, `VITE_API_BASE_URL` has no trailing slash, and the backend CORS origin exactly matches the Vite origin.

## Jobs never complete

In local mode, keep `REDIS_URL=fakeredis://` and `RQ_ASYNC=False`. In async mode, use real Redis and run `python worker.py` with the same environment as the API.

## Cloud import remains disabled

Configure the provider client/secret and exact callback URL, restart the backend, and inspect `/admin/status`. Test with a dedicated provider tenant and synthetic files.

## Verification email is not sent

Local mode intentionally returns a manual verification link when SMTP is absent. Production registration is blocked until SMTP and `FROM_EMAIL` are configured.

## Readiness fails while liveness passes

`/healthz` confirms the process is alive. `/readyz` also checks dependencies; inspect database and Redis connectivity before routing traffic.
