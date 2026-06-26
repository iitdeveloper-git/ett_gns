# GNS Core Stabilization Report

Date: 2026-06-26

## Completed features and fixes

- Fixed Python package discovery so `uv sync` works.
- Removed local duplicate empty Alembic fallback-provider revisions from the active history and repaired the ignored dev database stamp.
- Added tenant/application selectors with search, inline create, auto-select, tenant-change app clearing, and stale local-storage recovery.
- Added dashboard guided onboarding for the complete first-send path.
- Added pre-save provider connection testing at `POST /api/v1/provider-configs/test-connection`.
- Added provider-config aliases for read, patch, test, replace-secret, activate, deactivate, default/unset-default, and safe archive.
- Added provider archive semantics that preserve notification history while destroying provider secret material.
- Updated provider UI with pre-save test gate and lifecycle actions.
- Added Swagger HTTP Bearer scheme for GNS application credentials.
- Changed notification runtime contract so `app_id` is optional and derived from the credential; supplied mismatches return `application_scope_mismatch`.
- Improved frontend error rendering with safe message, code, request ID, and recovery hint.

## Migration and packaging status

- `uv sync`: pass.
- Alembic current head: `2ba920e67437`.
- `uv run alembic downgrade base`: pass.
- `uv run alembic upgrade head`: pass.
- `uv run alembic check`: pass, no drift detected.
- PostgreSQL verification remains to be executed in Docker/CI because local Docker/PostgreSQL is unavailable.

## Test and quality status

- Backend tests: 30 passed.
- Backend coverage: 78%.
- Ruff: pass.
- Strict mypy subset: pass for 18 production files.
- Frontend lint: pass.
- Frontend typecheck/build: pass through `next build`.
- Docker Compose: blocked locally, `docker: command not found`.
- k6 load tests: blocked locally, `k6: command not found`.

## Provider management and SMTP validation

SMTP supports SSL/TLS, STARTTLS, authentication, timeout, sender, HTML/text, reply-to and normalized adapter failures. Pre-save and saved-provider test paths use the same adapter boundary. Live SMTP validation requires real credentials or Mailpit through Docker Compose.

## Notification E2E status

The local backend test suite covers onboarding primitives, credential creation, notification acceptance, idempotency, application scope enforcement, worker delivery, retry, DLQ/reconcile, callbacks, and provider selection. Full browser+worker+PostgreSQL E2E remains blocked by local Docker availability.

## Limitations and blockers

- Docker is unavailable locally.
- Live provider credentials are unavailable.
- Live OIDC provider is unavailable.
- Staging/cloud target is unavailable.
- k6 is unavailable.

## Commit list

- `f431f6d feat: complete multi-tenant notification platform`
- Current stabilization changes are ready to commit after final verification.

## Exact next actions

1. Run `docker compose --profile local up --build` on a machine with Docker.
2. Verify Mailpit SMTP send, worker completion, retry, DLQ replay, and operations timeline.
3. Configure OIDC issuer/audience and verify each role mapping.
4. Configure sandbox provider credentials for SMS, push, Telegram, WhatsApp, webhook, and SMTP.
5. Deploy staging and run k6 acceptance/idempotency tests.
