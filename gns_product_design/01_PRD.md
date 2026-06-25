# Product Requirements Document

## 1. Product vision

Build a reusable notification platform where multiple applications register once, define events and templates, optionally configure their own providers, and later send notifications using only an application ID, event key, recipient, and event data.

## 2. Problem

Without GNS, every product separately implements SMTP, SMS, retries, templates, provider credentials, delivery logs, rate limits, and error handling. This causes duplication, inconsistent security, provider lock-in, and poor reliability.

## 3. Users

- Platform administrators
- Tenant administrators
- Application owners
- Template designers
- Backend services
- Operations engineers
- Security and audit teams

## 4. Primary capabilities

1. Tenant and application registration
2. Per-app credentials and RBAC
3. Event registration with JSON Schema
4. Versioned templates by channel, locale, and variant
5. Optional app-specific provider configuration
6. Default-provider fallback when no app provider exists
7. Asynchronous notification delivery
8. Retries, dead-letter queue, and replay
9. Delivery status and provider callbacks
10. Usage quotas, rate limits, audit logs, and observability
11. Extensible channel adapters

## 5. Goals

- Multi-tenant from day one
- At-least-once internal delivery semantics
- p95 API enqueue latency below 250 ms
- Horizontal scaling to 1,000+ requests/second
- Strong tenant isolation
- Add a new channel without redesigning the runtime API
- Immutable published template versions
- Safe default sender behavior

## 6. Non-goals for MVP

- Marketing campaign builder
- Customer data platform
- Visual drag-and-drop journey orchestration
- Exactly-once external delivery guarantee
- Full billing engine

## 7. Success metrics

- Delivery success rate by provider/channel
- Queue age
- Retry and DLQ rates
- Time to onboard a new app
- Template rendering failure rate
- Tenant abuse detection rate
- Provider latency and failure rate

## 8. Key product rule

Applications describe **what happened**. GNS decides **how the message is rendered and delivered**.
