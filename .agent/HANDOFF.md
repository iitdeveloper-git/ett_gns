# Handoff

Last updated: 2026-06-26

The GNS Core stabilization goal is complete for all work executable without external infrastructure or credentials. The checkout originally contained only an older Flask prototype; the referenced foundation commits were absent.

## Completed

- Production FastAPI modular monolith with SQLAlchemy and Alembic
- Multi-tenant control plane, hashed credentials, RBAC/OIDC boundary
- Events, schema compatibility, sandboxed templates and provider management
- Durable notification acceptance, idempotency, transactional outbox, workers, retries, DLQ, scheduling, cancellation and reconciliation
- SMTP, webhook, SMS, push, Telegram and WhatsApp adapters with deterministic/local contract verification
- Signed replay-safe callbacks and legal delivery transitions
- Quotas, usage, audits, logs, metrics and tracing
- Responsive connected Next.js admin console
- Tenant/application selectors, stale-ID recovery and guided onboarding
- Provider pre-save connection testing, provider-config aliases, safe archive and default lifecycle
- Swagger bearer authentication and credential-derived notification app scope
- Docker/Compose and managed-container deployment artifacts
- CI/CD, SBOM/image/secret scanning configuration
- Complete required documentation, security verification and load-test definitions

## Verification

- 30 backend tests pass
- 75.54% scoped backend coverage
- Ruff and strict mypy pass
- Alembic upgrade/check/downgrade pass
- Frontend lint, strict typecheck, three unit tests and production build pass
- One Playwright E2E test passes
- Desktop/mobile browser QA passes with no console warnings
- Python and npm audits report zero known vulnerabilities

## External blockers

Docker, provider credentials, OIDC provider, staging target/cloud permissions, and representative load-test environment are unavailable. Exact next actions are listed in `.agent/TASKS.md` and `docs/release-checklist.md`.
