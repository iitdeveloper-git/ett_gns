# Changelog

## 0.2.1 - 2026-06-26

- Fixed `uv sync` package discovery.
- Added GNS Core stabilization matrix, security verification, and stabilization report.
- Replaced manual workspace ID entry with tenant/application selectors and stale selection recovery.
- Added guided onboarding checklist to the dashboard.
- Added provider pre-save connection testing, provider-config route aliases, safe archive, default/unset-default, and provider UI lifecycle actions.
- Added Swagger HTTP Bearer scheme for application credentials.
- Made notification `app_id` optional and enforced credential-derived application scope.
- Improved frontend error rendering with machine code and request ID.

## 0.2.0 - 2026-06-26

- Migrated the production entry point from the Flask prototype to FastAPI.
- Added multi-tenant persistence, credentials, RBAC/OIDC boundary, events, templates and providers.
- Added durable runtime acceptance, idempotency, outbox, delivery attempts, retries, DLQ and callbacks.
- Added six channel adapter boundaries, sender integrity, quotas, audits, metrics and tracing.
- Added the Next.js administration console.
- Added Alembic, Compose, managed-container deployment, CI/CD, security verification and load-test definitions.

Legacy Flask modules remain temporarily for migration compatibility and are not the production entry point.
