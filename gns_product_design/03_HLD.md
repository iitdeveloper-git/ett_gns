# High-Level Design

```mermaid
flowchart LR
    APPS[Application Backends] --> GW[API Gateway]
    ADM[Admin UI] --> GW
    GW --> AUTH[Authentication and Tenant Guard]
    AUTH --> API[GNS API]
    API --> DB[(PostgreSQL)]
    API --> OUTBOX[Transactional Outbox]
    OUTBOX --> Q[(Durable Queues)]
    Q --> EW[Email Workers]
    Q --> SW[SMS Workers]
    Q --> WW[Webhook Workers]
    Q --> PW[Push Workers]
    Q --> WAW[WhatsApp Workers]
    Q --> TGW[Telegram Workers]
    EW --> PROVIDERS[External Providers]
    SW --> PROVIDERS
    WW --> PROVIDERS
    PW --> PROVIDERS
    WAW --> PROVIDERS
    TGW --> PROVIDERS
    PROVIDERS --> CALLBACKS[Callback API]
    CALLBACKS --> DB
```

## Services

### API Gateway
TLS, WAF, request limits, rate limiting, routing.

### Management API
Apps, credentials, events, templates, providers, quotas, users.

### Runtime API
Validation, idempotency, persistence, queueing, status lookup.

### Delivery workers
Channel-specific processing and failure isolation.

### Callback processor
Verifies provider signatures and normalizes delivery events.

### Scheduler
Scheduled notifications, retries, retention, provider health checks.

## Storage

- PostgreSQL: system of record
- Secret manager: provider credentials
- Durable queue: SQS/RabbitMQ/Redis Streams
- Object storage: attachments/assets
- Metrics/log/tracing platform

## Scaling

Scale APIs, workers, callbacks, and schedulers independently. Use separate channel queues so one provider outage does not block other channels.

## Final platform stack decision

The target implementation uses FastAPI, PostgreSQL, SQLAlchemy, Alembic, Celery, RabbitMQ, Redis, restricted Jinja2, and a Next.js/TypeScript administration console. The deployment begins as a modular monolith plus channel-specific workers.
