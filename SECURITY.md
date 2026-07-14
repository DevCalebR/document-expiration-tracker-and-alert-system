# Security policy

Keep this repository private. Only the latest commit on `main` is supported.

Report issues directly to the repository owner; do not create public disclosure artifacts. Reproduction material must use synthetic documents and remove tokens, credentials, emails, filenames, storage keys, extracted text, dates, and database records.

Security invariants:

- Validate upload size, extension, content handling, and generated storage keys.
- Scope every document, job, export, and cloud operation to the authenticated user/role.
- Encrypt OAuth tokens with a dedicated production key.
- Keep local eager/fakeredis behavior out of production.
- Restrict hosts and CORS, use HTTPS, and store production secrets in a secret manager.
- Do not log document contents, authorization headers, tokens, or credentials.
