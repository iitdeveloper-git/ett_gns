# API Design

## Management APIs

### Register app

```http
POST /api/v1/apps
```

```json
{
  "name": "IIT Developer",
  "slug": "iit-developer",
  "default_locale": "en-IN",
  "timezone": "Asia/Kolkata"
}
```

### Register event

```http
POST /api/v1/apps/{app_id}/events
```

```json
{
  "event_key": "contact.inquiry.received",
  "allowed_channels": ["email"],
  "schema": {
    "type": "object",
    "required": ["user_name", "user_email", "project_message"],
    "properties": {
      "user_name": {"type": "string"},
      "user_email": {"type": "string", "format": "email"},
      "project_message": {"type": "string", "maxLength": 5000}
    },
    "additionalProperties": false
  }
}
```

### Create template

```http
POST /api/v1/apps/{app_id}/events/{event_key}/templates
```

### Register provider

```http
POST /api/v1/apps/{app_id}/providers
```

```json
{
  "channel": "email",
  "provider_type": "smtp",
  "public_config": {
    "host": "mail.iitdeveloper.com",
    "port": 465,
    "security": "ssl",
    "username": "info@iitdeveloper.com",
    "from_name": "IIT Developer",
    "from_email": "info@iitdeveloper.com"
  },
  "secret": {"password": "write-only"},
  "fallback_policy": "none"
}
```

## Runtime API

```http
POST /api/v1/notifications
Authorization: Bearer <app-key>
Idempotency-Key: inquiry-123
```

```json
{
  "app_id": "app_iitdeveloper",
  "event_key": "contact.inquiry.received",
  "channel": "email",
  "recipient": {"email": "customer@example.com"},
  "data": {
    "user_name": "Ravi",
    "user_email": "customer@example.com",
    "project_message": "Need a website"
  },
  "metadata": {
    "source": "website",
    "correlation_id": "req_123"
  }
}
```

## Security constraints

Runtime clients may not pass arbitrary HTML, sender addresses, provider secrets, or unrestricted template paths.

## Public website pattern

```text
Browser -> app backend/Netlify Function -> GNS
```

Never expose the GNS app key in browser JavaScript.
