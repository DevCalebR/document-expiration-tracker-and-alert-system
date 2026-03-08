# DocExpire Frontend

React + Vite frontend for DocExpire.

## What it does
- Handles login, registration, and email verification
- Uploads and lists documents already stored for the current user
- Starts async processing jobs and polls backend job status
- Shows expiring-soon results, AI analysis, CSV export, and extracted text previews
- Connects Google Drive, Dropbox, and OneDrive through popup OAuth flows
- Exposes admin-only operations for queue status, alert runs, and SMTP test email

## Local setup
```bash
cd /Users/caleb/Desktop/DocExpire/frontend
npm install
cp .env.example .env
npm run dev
```

Default frontend URL: [http://localhost:5173](http://localhost:5173)

## Environment
`frontend/.env.example` contains the only required setting:
```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Use a different backend origin only if the API is not running on the default local address.

## Quality checks
### Tests
```bash
cd /Users/caleb/Desktop/DocExpire/frontend
npm test -- --run
```

### Production build
```bash
cd /Users/caleb/Desktop/DocExpire/frontend
npm run build
```

## Runtime notes
- The UI uses background job processing first and only offers sync processing as an explicit fallback.
- Cloud provider buttons stay disabled or show clear error states when backend credentials are missing.
- The admin panel is visible only for users with the `admin` role.
