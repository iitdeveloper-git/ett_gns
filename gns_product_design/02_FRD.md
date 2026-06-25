# Functional Requirements Document

## Application management

- Create, update, disable, archive application
- Generate, rotate, revoke API credentials
- Configure branding, locale, timezone, quotas
- Assign roles and permissions

## Event management

- Unique event key per application
- JSON Schema for event data
- Versioned schemas
- Allowed channel list
- Recipient policy
- Enable/disable event

## Template management

Template identity:

```text
app + event + channel + locale + variant
```

Lifecycle:

```text
draft -> validated -> published -> deprecated -> archived
```

Requirements:

- Preview with sample data
- Send test message
- Validate variables against event schema
- Publish immutable version
- Roll back to a previous version
- Support HTML/text/JSON/channel-specific formats

## Provider management

- Platform default provider per channel
- Optional app-specific provider
- Provider connectivity test
- Encrypted credentials
- Health status
- Explicit fallback policy

Recommended fallback rule:

```text
custom provider exists and works -> use custom
no custom provider -> use default if allowed
custom provider fails auth -> fail; do not silently use default
```

## Runtime send

Request contains:

- app_id
- event_key
- channel
- recipient
- event data
- locale/variant optional
- metadata optional
- idempotency key

Response:

```json
{
  "notification_id": "ntf_...",
  "status": "queued"
}
```

## Delivery processing

- Validate app and event
- Resolve template
- Resolve provider
- Render safely
- Queue per channel
- Record attempts
- Retry temporary failures
- Move exhausted failures to DLQ
- Accept delivery callbacks

## Statuses

```text
accepted
queued
processing
sent
delivered
deferred
failed
dead_lettered
cancelled
```

## Non-functional requirements

- Runtime API: 99.9% target availability
- Management API: 99.5%
- Durable persistence before acknowledgment
- All tenant-sensitive operations audited
- No provider secret returned after creation
