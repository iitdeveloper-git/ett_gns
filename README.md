---
title: Generic Notification Service
emoji: 🚀
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 5000
pinned: false
---

# 🔔 Generic Notification Service

<p align="center">
  <strong>One notification platform. Every channel. Reliable delivery.</strong>
</p>

<p align="center">
  GNS is a multi-tenant, API-first notification infrastructure for sending transactional and operational messages across email, SMS, push, webhook, Telegram, WhatsApp, and future in-app channels.
</p>

<p align="center">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-Backend-009688?style=flat-square">
  <img alt="Next.js" src="https://img.shields.io/badge/Next.js-Admin%20Console-000000?style=flat-square">
  <img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-Database-336791?style=flat-square">
  <img alt="RabbitMQ" src="https://img.shields.io/badge/RabbitMQ-Queue-FF6600?style=flat-square">
  <img alt="Redis" src="https://img.shields.io/badge/Redis-Cache-DC382D?style=flat-square">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square">
</p>

---

## ✨ What is GNS?

Every application eventually needs to send notifications:

- welcome emails
- password resets
- OTPs
- appointment reminders
- payment receipts
- admission updates
- system alerts
- WhatsApp or Telegram messages
- webhooks to third-party systems

Without a shared platform, each application usually rebuilds the same logic for templates, retries, providers, delivery status, authentication, audit logs, and failure handling.

**GNS solves that problem once.**

```text
Your Application
      │
      │  event + recipient + data
      ▼
┌───────────────────────────────┐
│             GNS               │
│                               │
│  Events → Templates → Routing │
│       → Queue → Workers       │
│       → Providers → Status    │
└───────────────────────────────┘
      │
      ├── Email
      ├── SMS
      ├── Push
      ├── Webhook
      ├── Telegram
      └── WhatsApp
```

---

## 🚀 Core Capabilities

### 🏢 Multi-Tenant Platform

- Tenant and application isolation
- Application-specific credentials
- Application-level providers
- Global default providers
- Role-based administration
- Audit-safe operational controls

### 🔐 Secure Application Credentials

- One-time API key reveal
- Hashed secret storage
- Expiration
- Revocation
- Rotation with overlap
- Permission scopes
- Last-used tracking

### 🧩 Event Contracts

Applications register events such as:

```text
user.welcome
appointment.reminder
payment.receipt
password.reset
```

Each event supports:

- versioned JSON Schema
- recipient policy
- allowed channels
- compatibility validation
- sample payloads
- schema history

### 🎨 Versioned Templates

- Draft creation
- Validation
- Live preview
- Test send
- Immutable publication
- Version history
- Rollback
- Locale support
- Variants
- Sandboxed rendering

Example:

```json
{
  "subject": "Welcome, {{ name }}",
  "html": "<h2>Hello {{ name }}</h2><p>Your account is ready.</p>",
  "text": "Hello {{ name }}. Your account is ready."
}
```

### 📡 Provider Management

- Pre-save provider connection testing
- Encrypted provider secrets
- Provider health checks
- Activate and deactivate
- Application-specific providers
- Global defaults
- Explicit fallback policies
- Safe archival
- Sender-integrity controls

Supported adapter boundaries:

- SMTP email
- Signed webhook
- Twilio-compatible SMS
- FCM-compatible push
- Telegram Bot API
- Meta WhatsApp Cloud API

### ⚙️ Durable Delivery Pipeline

- Transactional outbox
- RabbitMQ queues
- Channel workers
- Retry policies
- Delivery attempts
- Dead-letter queue
- Scheduled delivery
- Cancellation
- Worker leases
- Reconciliation
- Idempotent notification acceptance

### 📊 Operational Visibility

- Notification lifecycle
- Provider health
- Queue depth
- Retry count
- Dead-letter status
- Audit trail
- Prometheus metrics
- OpenTelemetry traces
- Structured logs

---

## 🧭 Guided Onboarding

The admin console guides operators through the complete setup:

```text
Tenant
  ↓
Application
  ↓
Event
  ↓
Template
  ↓
Provider
  ↓
Credential
  ↓
Test Notification
```

Each step shows completion state so a new application can be onboarded without directly editing the database.

---

## 🖥️ Admin Console

The Next.js administration console includes:

- Dashboard
- Applications
- Events
- Templates
- Providers
- Notifications
- Credentials
- Audit logs

The UI supports:

- searchable tenant and application selectors
- stale workspace recovery
- template preview and publishing
- provider testing
- safe secret handling
- delivery troubleshooting
- guided onboarding

---

## 🧪 Example: Send a Welcome Email

### 1. Register an event

```text
Event key: user.welcome
Channel: email
```

Example schema:

```json
{
  "type": "object",
  "required": ["name"],
  "properties": {
    "name": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

### 2. Publish a template

```json
{
  "subject": "Welcome {{ name }}",
  "html": "<h2>Hello {{ name }}</h2><p>Welcome to our platform.</p>",
  "text": "Hello {{ name }}. Welcome to our platform."
}
```

### 3. Send the notification

```bash
export GNS_API_KEY='gns_your_application_key'

curl -X POST \
  'http://127.0.0.1:5000/api/v1/notifications' \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: welcome-user-001' \
  -H "Authorization: Bearer $GNS_API_KEY" \
  -d '{
    "event_key": "user.welcome",
    "channel": "email",
    "recipient": {
      "email": "user@example.com"
    },
    "data": {
      "name": "Ravi"
    },
    "locale": "en",
    "variant": "default",
    "priority": 5,
    "metadata": {
      "source": "website"
    }
  }'
```

Expected response:

```json
{
  "id": "ntf_example",
  "status": "accepted"
}
```

Delivery lifecycle:

```text
accepted
→ queued
→ processing
→ provider_accepted
→ sent
→ delivered
```

> Delivery states such as `delivered`, `opened`, and `clicked` are used only when the provider supplies reliable callback data.

---

## 🏗️ Architecture

```text
┌────────────────────┐
│ Client Applications│
└─────────┬──────────┘
          │ HTTPS
          ▼
┌────────────────────┐
│ FastAPI API        │
│                    │
│ Auth               │
│ Events             │
│ Templates          │
│ Providers          │
│ Notifications      │
└─────────┬──────────┘
          │
          ├──────────────► PostgreSQL
          │
          ├──────────────► Redis
          │
          ▼
┌────────────────────┐
│ Transactional      │
│ Outbox Publisher   │
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ RabbitMQ           │
└─────────┬──────────┘
          ▼
┌──────────────────────────────────┐
│ Channel Workers                  │
│ Email · SMS · Push · Webhook     │
│ Telegram · WhatsApp              │
└──────────────────────────────────┘
```

---

## ⚡ Quick Start

### Requirements

- Python 3.13+
- Node.js 20+
- PostgreSQL or SQLite for local development
- Redis
- RabbitMQ

### Backend

```bash
cp sample.env .env

uv sync
uv run alembic upgrade head
uv run uvicorn ett_gns_app.main:app --reload --port 5000
```

API:

```text
http://localhost:5000
```

Swagger:

```text
http://localhost:5000/docs
```

### Admin Console

```bash
cd admin
npm ci
npm run dev
```

Open:

```text
http://localhost:3000
```

Development mode uses safe local identity headers. Production rejects development identity mode.

---

## 🐳 Docker Compose

Start the complete local stack:

```bash
docker compose up -d
```

Or with Podman:

```bash
podman compose up -d
```

Typical services:

```text
api
admin
postgres
redis
rabbitmq
outbox-publisher
scheduler
worker-email
worker-sms
worker-push
worker-webhook
worker-telegram
worker-whatsapp
```

Inspect services:

```bash
docker compose ps
docker compose logs -f api outbox-publisher worker-email
```

---

## 🔒 Security

GNS includes:

- Hashed API credentials
- Encrypted provider secrets
- One-time secret reveal
- Tenant and application isolation
- OIDC verification boundary
- Development identity restricted to local environments
- Webhook SSRF protection
- Signed callbacks
- Replay protection
- Rate limiting
- Template sandboxing
- Audit logging
- Secret redaction
- Sender-domain integrity controls

Never place API keys or provider passwords in:

- screenshots
- chat messages
- logs
- source control
- documentation

Use a secret manager or environment variables.

---

## ✅ Verification

### Backend

```bash
uv run ruff check .

uv run mypy \
  ett_gns_app/main.py \
  ett_gns_app/settings.py \
  ett_gns_app/security.py \
  ett_gns_app/database.py \
  ett_gns_app/models.py \
  ett_gns_app/api.py \
  ett_gns_app/management_api.py \
  ett_gns_app/operations_api.py \
  ett_gns_app/schemas.py \
  ett_gns_app/template_service.py \
  ett_gns_app/secrets.py \
  ett_gns_app/resolution.py \
  ett_gns_app/delivery.py \
  ett_gns_app/callbacks.py \
  ett_gns_app/observability.py \
  ett_gns_app/quotas.py \
  ett_gns_app/channels/contracts.py \
  ett_gns_app/channels/adapters.py

uv run pytest
uv run alembic check
```

### Frontend

```bash
cd admin

npm run lint
npm run typecheck
npm test
npm run build
```

---

## 📚 Documentation

- [Admin onboarding](docs/admin-onboarding.md)
- [Send your first notification](docs/send-first-notification.md)
- [Provider management](docs/provider-management.md)
- [Local development](docs/local-development.md)
- [API reference](docs/api.md)
- [Deployment guide](docs/deployment.md)
- [Security](docs/security.md)
- [Operations](docs/operations.md)
- [Troubleshooting](docs/troubleshooting.md)

---

## 🧱 Project Structure

```text
gns/
├── ett_gns_app/
│   ├── api.py
│   ├── management_api.py
│   ├── operations_api.py
│   ├── models.py
│   ├── schemas.py
│   ├── delivery.py
│   ├── resolution.py
│   ├── callbacks.py
│   ├── observability.py
│   └── channels/
├── admin/
├── migrations/
├── templates/
├── tests/
├── observability/
├── docs/
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

## 🛣️ Roadmap

### GNS Core

- Production hardening
- Provider diagnostics
- Delivery analytics
- More SDKs
- Hosted deployment profiles

### In-App Notifications

- Real-time notifications
- Toast components
- Notification bell
- Notification center
- Read/unread state
- React/Next.js SDK

### GNS Engage.AI

- Campaign management
- Customer replies
- Unified conversations
- AI response suggestions
- Knowledge-grounded answers
- Intent and sentiment analysis
- Workflow automation
- Campaign intelligence

---

## 🌍 Use Cases

### Healthcare

- Appointment reminders
- Reschedule requests
- Test-report notifications
- Payment alerts
- Operational messaging

### Education

- Admission updates
- Fee reminders
- Attendance alerts
- Parent communication
- Examination notifications

### SaaS

- Welcome messages
- Password resets
- Billing notifications
- Product lifecycle events
- Security alerts

### Agencies and Service Businesses

- Lead follow-ups
- Campaign delivery
- Client notifications
- Booking confirmations
- Support messages

---

## 🤝 Contributing

Contributions are welcome.

Before opening a pull request:

1. Read the architecture and security documentation.
2. Add tests for all behavioral changes.
3. Run backend and frontend verification.
4. Update documentation.
5. Do not introduce insecure shortcuts.
6. Do not commit secrets or customer data.

---

## ⚠️ Current Validation Status

Live delivery depends on valid provider credentials.

Docker Compose and staging deployment must be reported truthfully based on the current environment. Mock adapters and local test servers do not count as live provider verification.

---

## 📄 License

Add your selected license here.

---

<p align="center">
  <strong>Built by IITDEVELOPER</strong>
</p>

<p align="center">
  Reliable notifications today. Intelligent engagement tomorrow.
</p>
