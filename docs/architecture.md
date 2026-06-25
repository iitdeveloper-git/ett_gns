# Architecture

GNS is a modular monolith with independently scalable asynchronous processes.

```text
Application/Admin -> FastAPI -> PostgreSQL
                           \-> transactional outbox
Outbox publisher -> RabbitMQ -> Celery delivery workers -> providers
Celery beat -> retry/reconciliation jobs
Provider callbacks -> signed callback API -> delivery events/PostgreSQL
Next.js admin -> FastAPI management/operations APIs
Redis -> Celery result state and deployment-time distributed services
```

PostgreSQL is the system of record. A runtime request is acknowledged only after the notification, immutable template/provider references, audit event, quota usage, and outbox event are committed.

Channel adapters implement validation and normalized `SendResult`/`AdapterError` contracts. Provider selection refuses silent fallback when any app-specific provider exists but is unhealthy. A tenant default is used only when its explicit `default_if_absent` policy allows it.

Published template versions are immutable. Resolution order is requested locale, app default, platform default; requested variant then `default`.

Internal delivery is at least once. External exactly-once delivery is impossible in general, so provider IDs, callbacks, and idempotency are retained for reconciliation.
