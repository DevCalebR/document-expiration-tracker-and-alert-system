# Contributing

This private repository processes documents, identity data, OAuth tokens, and email addresses. Use generated fixtures and dedicated test-provider tenants only.

1. Create a focused branch from `main`.
2. Configure the local profile from the checked-in environment examples.
3. Preserve auth, storage-path, token-encryption, upload-validation, and tenant boundaries.
4. Add backend or frontend tests for changed behavior.
5. Run backend tests, frontend tests, and the frontend production build.

Never commit `.env`, uploaded files, OCR output, database files, cloud tokens, SMTP credentials, object-store keys, real email addresses, or screenshots containing real documents.
