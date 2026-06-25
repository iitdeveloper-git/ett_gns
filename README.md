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
python3 -m pip install -r requirements-dev.txt
alembic upgrade head
uvicorn ett_gns_app.main:app --reload --port 5000
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
ruff format --check .
ruff check .
mypy ett_gns_app
pytest --cov=ett_gns_app --cov-fail-under=75
alembic check
cd admin && npm run lint && npm run typecheck && npm test && npm run build
```

See [docs/local-development.md](docs/local-development.md), [docs/api.md](docs/api.md), and [docs/deployment.md](docs/deployment.md).
