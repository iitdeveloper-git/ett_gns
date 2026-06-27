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

## Fixing `SMTP_TLS_FAILED`

If the UI shows:

```text
SMTP_TLS_FAILED: certificate verify failed: unable to get local issuer certificate
```

GNS reached the SMTP server, but the TLS certificate chain could not be verified. Fix the mail server certificate chain rather than disabling verification:

1. Install the intermediate CA certificates on the SMTP server.
2. Confirm port `465` serves implicit TLS and `587` serves STARTTLS.
3. Re-test with an SSL checker or `openssl s_client -connect mail.example.com:465 -showcerts`.
4. If using a private CA, install that CA in the container/host trust store.

GNS intentionally does not provide a production “ignore certificate errors” switch.
