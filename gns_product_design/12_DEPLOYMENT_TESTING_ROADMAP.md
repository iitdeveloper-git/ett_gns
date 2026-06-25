# Deployment, Testing, and Roadmap

## Services

```text
gns-api
gns-outbox-publisher
gns-worker-email
gns-worker-sms
gns-worker-webhook
gns-worker-push
gns-worker-whatsapp
gns-worker-telegram
gns-callback
gns-scheduler
postgres
redis/rabbitmq
```

## Environments

local, development, staging, production. Each uses separate DB, queue, secrets, providers, and callback URLs.

## Health endpoints

```text
/health/live
/health/ready
/health/dependencies
```

## Testing

- Unit: schema, provider resolution, sender rules, retry classification
- Integration: DB, queue, SMTP/provider sandbox
- Contract: every adapter
- E2E: register app -> event -> template -> provider -> send -> callback
- Security: tenant isolation, template injection, replay, SSRF, rate limits
- Load: API throughput, queue lag, worker scaling
- Chaos: worker crash, provider timeout, DB failover, duplicate callback

## Roadmap

### Phase 1: Foundation
Apps, credentials, events, templates, email, basic logs.

### Phase 2: Reliable MVP
Queue, outbox, retries, DLQ, idempotency, provider configs, status API.

### Phase 3: Multi-channel
SMS, webhook, push, Telegram, WhatsApp, callbacks.

### Phase 4: Platform
Admin UI, RBAC, quotas, audit console, localization, usage metering.

### Phase 5: Enterprise
Multi-region, data residency, SSO, mTLS, dedicated queues, SLA reporting.

## Deployment baseline

Deploy containerized API and channel workers with managed PostgreSQL, RabbitMQ, and Redis first. Kubernetes is a later-stage decision, not an MVP requirement.
