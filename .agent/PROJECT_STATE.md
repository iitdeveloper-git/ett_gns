# Project State

Last updated: 2026-06-26

## Recovery

- Branch: `main`, original HEAD `1d42fd4`.
- Referenced commits `cc44128` and `fdfbcca` were absent; implementation was rebuilt from the checked-in design documents.
- The legacy Flask prototype remains only as a migration compatibility path. FastAPI is the production entry point.

## Implemented state

- Multi-tenant FastAPI/SQLAlchemy/Alembic platform
- Tenant/application lifecycle, hashed credentials, rotation/revocation, RBAC and OIDC boundary
- Events and versioned JSON Schemas
- Sandboxed versioned templates, preview, test send, publish and rollback
- Encrypted provider records, explicit fallback, sender integrity and six channel adapters
- Durable notification/idempotency/outbox models, Celery workers, leases, retries, DLQ, scheduling, cancellation and reconciliation
- Signed/idempotent callbacks and delivery timelines
- Quotas, usage, audits, structured logs, Prometheus and OpenTelemetry
- Connected Next.js administration console
- Searchable tenant/application selectors, stale-ID recovery, guided onboarding and provider pre-save testing
- Provider-config compatibility endpoints, safe provider archive and Swagger bearer auth
- CI/CD, Compose, Render blueprint, security verification, operations docs and load-test definitions

## Verified

- Ruff format/lint: pass
- Strict mypy: pass for 18 production source files
- Backend: all 30 tests pass
- Scoped backend coverage: 78%
- Alembic upgrade/check/downgrade: pass
- Frontend lint/type/unit/build: pass
- Playwright: 1 pass
- Browser QA: desktop/mobile/API integration, no console warnings
- Python and npm vulnerability audits: clean

## External blockers

- Docker executable unavailable
- Live provider credentials unavailable
- Live OIDC provider unavailable
- Staging/cloud target unavailable
- k6 unavailable and no representative deployment
