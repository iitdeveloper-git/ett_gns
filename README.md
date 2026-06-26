# ETT Generic Notification Service

GNS is a multi-tenant notification platform for applications that register events, publish versioned templates, select verified providers, and submit durable asynchronous notifications through one runtime API.

## Implemented

- FastAPI management and runtime APIs with OpenAPI
- Tenant/application lifecycle and tenant isolation
- Hashed application API keys with one-time reveal, expiry, overlap rotation, revocation and last-used tracking
- Development identity mode plus production OIDC verification boundary and role permissions
- Versioned JSON Schemas with compatibility checks
- Sandboxed templates with validation, preview, test send, immutable publication, rollback, locale and variant resolution
- Encrypted provider secrets, health, activation, app/default selection and sender-integrity rules
- Searchable tenant/application selectors, guided onboarding, provider pre-save testing and safe provider archive in the admin console
- First-class in-app notifications with durable notification center records, SSE, read/unread state, preferences, React SDK and demo app
- SMTP, signed webhook, Twilio-compatible SMS, FCM-compatible push, Telegram Bot and Meta WhatsApp adapter boundaries
- Durable notification/idempotency/outbox records, scheduling fields, cancellation, worker leases, retries, DLQ and reconciliation
- Signed, replay-safe, idempotent provider callbacks and normalized delivery events
- Quotas, usage buckets, audit events, structured logs, Prometheus metrics and OpenTelemetry spans
- Connected Next.js admin console
- Alembic migrations, Compose topology, Render deployment blueprint and CI/CD workflows

Live delivery remains dependent on provider credentials. Docker Compose and staging deployment are not claimed as verified in the current environment because Docker and a staging target are unavailable.

## Quick start

```bash
cp sample.env .env
uv sync
uv run alembic upgrade head
uv run uvicorn ett_gns_app.main:app --reload --port 5000
```

In another terminal:

```bash
cd admin
npm ci
npm run dev
```

Open `http://localhost:3000`. Development admin requests use the safe local identity headers built into the console. Production rejects development identity mode.

## Verification

```bash
uv run ruff check .
uv run mypy ett_gns_app/main.py ett_gns_app/settings.py ett_gns_app/security.py ett_gns_app/database.py ett_gns_app/models.py ett_gns_app/api.py ett_gns_app/management_api.py ett_gns_app/in_app.py ett_gns_app/operations_api.py ett_gns_app/schemas.py ett_gns_app/template_service.py ett_gns_app/secrets.py ett_gns_app/resolution.py ett_gns_app/delivery.py ett_gns_app/callbacks.py ett_gns_app/observability.py ett_gns_app/quotas.py ett_gns_app/channels/contracts.py ett_gns_app/channels/adapters.py
uv run pytest
uv run alembic check
cd admin && npm run lint && npm run typecheck && npm test && npm run build
```

See [docs/admin-onboarding.md](docs/admin-onboarding.md), [docs/send-first-notification.md](docs/send-first-notification.md), [docs/provider-management.md](docs/provider-management.md), [docs/in-app-overview.md](docs/in-app-overview.md), [docs/local-development.md](docs/local-development.md), [docs/api.md](docs/api.md), and [docs/deployment.md](docs/deployment.md).
