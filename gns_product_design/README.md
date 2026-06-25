# Generic Notification Service (GNS)

A scalable, secure, multi-tenant notification platform for Email, SMS, Webhook, Push, WhatsApp, Telegram, Slack, Teams, Discord, and future channels.

## Core idea

Applications send **business events**, not raw templates:

```text
app_id + event_key + channel + recipient + event_data
```

GNS handles authentication, tenant isolation, schema validation, template resolution, provider selection, queueing, retries, delivery tracking, and observability.

## Document set

- `01_PRD.md` — Product requirements
- `02_FRD.md` — Functional requirements
- `03_HLD.md` — High-level design
- `04_LLD.md` — Low-level design
- `05_API_DESIGN.md` — Management/runtime APIs
- `06_DATA_MODEL.md` — Database and domain model
- `07_SECURITY_MULTI_TENANCY.md` — Security and tenant isolation
- `08_CHANNELS_AND_PROVIDERS.md` — Channel/provider architecture
- `09_RELIABILITY_SCALE.md` — Queueing, retries, DLQ, idempotency
- `10_TEMPLATE_SYSTEM.md` — Templates, schemas, versions, localization
- `11_OBSERVABILITY_OPERATIONS.md` — Logs, metrics, incidents
- `12_DEPLOYMENT_TESTING_ROADMAP.md` — Deployment, testing, implementation phases
- `sample.env`
- `docker-compose.example.yml`

## Technology stack decision

See `13_TECH_STACK_AND_ENGINEERING_STANDARDS.md` for the finalized production stack, migration plan, service layout, queue topology, deployment approach, and engineering standards.
