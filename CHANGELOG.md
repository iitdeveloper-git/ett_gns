# Changelog

## 0.2.0 - 2026-06-26

- Migrated the production entry point from the Flask prototype to FastAPI.
- Added multi-tenant persistence, credentials, RBAC/OIDC boundary, events, templates and providers.
- Added durable runtime acceptance, idempotency, outbox, delivery attempts, retries, DLQ and callbacks.
- Added six channel adapter boundaries, sender integrity, quotas, audits, metrics and tracing.
- Added the Next.js administration console.
- Added Alembic, Compose, managed-container deployment, CI/CD, security verification and load-test definitions.

Legacy Flask modules remain temporarily for migration compatibility and are not the production entry point.
