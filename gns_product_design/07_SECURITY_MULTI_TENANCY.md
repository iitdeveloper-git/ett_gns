# Security and Multi-Tenancy

## Tenant hierarchy

```text
Tenant -> Applications -> Events/Templates/Providers/Notifications
```

## Identity rules

- Tenant/app identity comes from authenticated credentials
- Never trust `app_id` from body without credential ownership validation
- One app credential cannot access another app

## Permissions

```text
apps:read
apps:write
credentials:rotate
events:manage
templates:write
templates:publish
providers:manage
notifications:send
notifications:read
notifications:retry
audit:read
```

## Secret management

- Encrypt provider secrets
- Return secrets only once
- Store API key hashes, not raw keys
- Never log secrets
- Rotate and revoke credentials
- Prefer Vault/AWS Secrets Manager/GCP Secret Manager/Azure Key Vault

## Sender integrity

When using default SMTP:

```text
From email = default authenticated sender
Display name = app-specific if allowed
Reply-To = app-specific verified address
```

An app may use its own sender domain only with a verified app-specific provider.

## Abuse controls

- Rate limits per app/tenant
- CAPTCHA for public forms
- Recipient policies
- Max payload/recipient count
- Anomaly detection
- Complaint/bounce monitoring
- Automatic suspension on abuse

## Template security

- Strict variable allowlist
- HTML sanitization
- Block scripts/iframes/forms
- Prevent server-side template injection
- Auto-escape user data
- No arbitrary filesystem/template paths
