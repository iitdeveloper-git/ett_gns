# Tasks

## Completed

- [x] Feature-completion audit and continuity recovery
- [x] FastAPI, typed configuration, SQLAlchemy, Alembic and test foundation
- [x] Tenant/application/credential/RBAC/event/schema/template/provider control plane
- [x] Durable runtime, idempotency, outbox, quotas and immutable snapshots
- [x] Workers, retries, DLQ, scheduling, cancellation and reconciliation
- [x] Six adapter boundaries, local mocks and SMTP integration
- [x] Signed callbacks, delivery receipts, audits, metrics and tracing
- [x] Connected responsive Next.js admin console
- [x] CI/CD, deployment profiles, security verification, operations docs and load-test scripts
- [x] Local lint/type/test/build/audit/migration verification
- [x] GNS Core stabilization audit matrix and final report
- [x] `uv sync` package discovery fix
- [x] Tenant/application selectors with stale-ID recovery
- [x] Guided onboarding checklist
- [x] Provider pre-save test, provider-config aliases, default/unset-default and safe archive
- [x] Swagger Bearer auth and credential-derived notification app scope
- [x] In-app notification channel, durable storage, SSE, user APIs, preferences and admin visibility
- [x] React/Next in-app SDK package and demo app source
- [x] SMTP TLS failure diagnostics and documentation

## Human/external actions

- [ ] Run Docker Compose E2E and record API/outbox/worker/scheduler/PostgreSQL/RabbitMQ/Redis/Mailpit results.
- [ ] Supply provider sandbox credentials and verify live delivery/callbacks.
- [ ] Supply OIDC issuer/audience and verify live role claims.
- [ ] Supply staging target/cloud permissions and execute deployment workflows.
- [ ] Run k6 scenarios against representative staging and record measurements.
- [ ] Replace local in-memory in-app SSE hub with Redis pub/sub or streams for multi-instance production.
- [ ] Integrate IAM role/group membership expansion for large fan-out.
- [ ] Configure deployment-specific alert destinations, retention and on-call ownership.
