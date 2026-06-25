# Technology Stack and Engineering Standards

## Recommended architecture style

Use a **modular monolith with independent asynchronous workers** for the first production versions. Do not begin with microservices. Keep domain boundaries strong so modules can be extracted later only when scale or team ownership justifies it.

## Production stack

| Layer | Technology |
|---|---|
| Language | Python 3.12+ |
| API framework | FastAPI |
| Validation | Pydantic v2 and JSON Schema |
| ORM | SQLAlchemy 2.x |
| Database | PostgreSQL 16+ |
| Migrations | Alembic |
| Task processing | Celery |
| Durable broker | RabbitMQ |
| Cache, locks, limits | Redis |
| Templates | Restricted/sandboxed Jinja2 |
| Admin frontend | Next.js + TypeScript |
| UI | Tailwind CSS + shadcn/ui |
| Data fetching | TanStack Query |
| Forms | React Hook Form + Zod |
| Template/schema editor | Monaco Editor |
| Human authentication | OIDC via Keycloak/Auth0/Cognito |
| Service authentication | API keys initially, signed JWT later, optional mTLS |
| Secret storage | Cloud secret manager or HashiCorp Vault |
| Observability | OpenTelemetry, Prometheus, Grafana, Loki, Tempo |
| Object storage | S3-compatible storage |
| Packaging | Docker |
| CI/CD | GitHub Actions |
| Testing | Pytest, Testcontainers, Playwright |

## Why this stack

- FastAPI gives typed APIs, OpenAPI generation, dependency injection, and strong request validation.
- PostgreSQL fits relational tenant, event, template, provider, notification, audit, and idempotency data.
- RabbitMQ provides durable routing, acknowledgements, channel-specific queues, retry queues, priorities, and dead-letter exchanges.
- Redis should be used for rate limiting, cache, distributed locks, and temporary state, not as the main system of record.
- Celery provides distributed workers, retries, scheduling, and channel-specific concurrency.
- Next.js and TypeScript are suitable for an admin console with template preview, schema editing, provider setup, and delivery logs.

## Service layout

```text
gns-api
gns-outbox-publisher
gns-worker-email
gns-worker-sms
gns-worker-webhook
gns-worker-push
gns-worker-whatsapp
gns-worker-telegram
gns-scheduler
gns-callback-processor
```

## Queue layout

```text
notifications.email
notifications.sms
notifications.webhook
notifications.push
notifications.whatsapp
notifications.telegram
notifications.retry
notifications.dead-letter
provider.callbacks
```

## Deployment recommendation

Start with managed services and containers:

- managed PostgreSQL
- managed RabbitMQ
- managed Redis
- Docker containers on ECS, Cloud Run, Render, Railway, or a comparable platform
- S3-compatible storage
- GitHub Actions

Move to Kubernetes only when worker count, autoscaling, multi-region deployment, or operational ownership justifies the added complexity.

## Current Flask migration strategy

Do not rewrite the complete existing GNS immediately.

1. Keep existing channel adapters and template helpers.
2. Add FastAPI as the new API layer.
3. Move controller logic into domain services.
4. Introduce SQLAlchemy repositories and Alembic migrations.
5. Add application, event, template, provider, and notification modules.
6. Add transactional outbox and RabbitMQ/Celery workers.
7. Migrate old Flask routes gradually.
8. Remove legacy routes only after contract and integration tests pass.

## Engineering standards

- Python type hints are mandatory.
- Domain services must not depend directly on Flask/FastAPI request objects.
- Provider adapters must implement a common contract.
- Published template versions are immutable.
- Secrets are referenced, never returned.
- Every runtime request must support idempotency.
- Every state change must be auditable.
- Public browser clients must never receive GNS service credentials.
- New channels must be added through adapters and capability metadata, not by modifying core event contracts.
