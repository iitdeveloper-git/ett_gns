# API

Interactive OpenAPI is available at `/docs`; the schema is `/openapi.json`.

## Administrative authentication

Development/test only:

```http
X-Admin-User: local-admin
X-Admin-Roles: platform_admin
X-Tenant-ID: tnt_...   # required for tenant-scoped non-platform roles
```

Production uses an OIDC bearer token whose issuer, audience, signature, expiry and roles are verified.

## Main control-plane resources

- `/api/v1/tenants`
- `/api/v1/tenants/{tenant_id}/apps`
- `/api/v1/apps/{app_id}/credentials`
- `/api/v1/apps/{app_id}/events`
- `/api/v1/apps/{app_id}/events/{event_key}/templates`
- `/api/v1/template-versions/{version_id}/validate|preview|test-send|publish`
- `/api/v1/tenants/{tenant_id}/providers`
- `/api/v1/apps/{app_id}/providers`
- `/api/v1/providers/{provider_id}/test|activate|deactivate`
- `/api/v1/audits`
- `/api/v1/operations/dashboard`
- `/api/v1/operations/notifications`

List endpoints use `limit` and `offset`. Errors include stable `detail.code` and `detail.message` fields plus `X-Request-ID`.

## Runtime

```http
POST /api/v1/notifications
Authorization: Bearer gns_<prefix>.<secret>
Idempotency-Key: unique-business-operation
```

```json
{
  "app_id": "app_...",
  "event_key": "account.welcome",
  "channel": "email",
  "recipient": {"email": "person@example.com"},
  "data": {"name": "Ravi"},
  "locale": "en-IN",
  "variant": "default",
  "priority": 5,
  "metadata": {"correlation_id": "corr_123"}
}
```

The response is `202`. Reusing the key with the same canonical request returns the original notification; different content returns `409 idempotency_conflict`.
