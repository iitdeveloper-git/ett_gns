# SMTP setup

Pre-test before registration:

```http
POST /api/v1/provider-configs/test-connection
```

```json
{
  "tenant_id": "tnt_...",
  "application_id": "app_...",
  "provider_type": "smtp",
  "channel": "email",
  "public_config": {
    "host": "mail.iitdeveloper.com",
    "port": 465,
    "security": "ssl",
    "username": "info@iitdeveloper.com",
    "from_email": "info@iitdeveloper.com",
    "timeout_seconds": 5
  },
  "secret_config": {
    "password": "write-only-value"
  }
}
```

Normalized failures include `SMTP_DNS_FAILED`, `SMTP_CONNECTION_FAILED`, `SMTP_TIMEOUT`, `SMTP_TLS_FAILED`, `SMTP_AUTH_FAILED`, `SMTP_SENDER_REJECTED`, `SMTP_PROVIDER_ERROR`, `CONFIG_INVALID`, and `SECRET_DECRYPTION_FAILED`.

