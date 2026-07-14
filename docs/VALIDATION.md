# Validation evidence

The current documentation-upgrade validation recorded:

- Backend: 10 tests passed with 2 warnings
- Frontend: 4 tests passed
- Frontend production build: succeeded
- Local smoke: health, readiness, registration, verification, login, provider status, upload, async processing, job polling, extraction, expiring-soon reporting, delete, and file listing
- Eager-mode worker: exited cleanly because a separate worker was not required
- Scheduler enqueue helper: completed in the local profile

## Commands

```bash
cd backend
source .venv/bin/activate
pytest -q

cd ../frontend
npm test -- --run
npm run build
```

## External validation still required

- Live Google Drive, Dropbox, and OneDrive OAuth handshakes
- SMTP delivery through the selected production provider
- AI analysis with a dedicated API key
- Representative OCR evaluation against rights-cleared fixtures
- Production PostgreSQL, Redis, object-storage, backup, and recovery exercises

These external checks must use synthetic data and dedicated test tenants.
