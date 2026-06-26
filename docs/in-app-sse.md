# In-App SSE

```http
GET /api/v1/in-app/stream
Authorization: Bearer <user-access-token>
Accept: text/event-stream
```

Development/test can use:

```http
Authorization: Bearer dev_user_usr_123
X-Tenant-ID: tnt_...
X-App-ID: app_...
X-Session-ID: ses_...
```

Production validates OIDC issuer, audience, signature, expiry, subject, tenant and application claims. Tokens must be sent in headers, never query strings.

Events:

- `connection.ready`
- `notification.created`
- `notification.updated`
- `heartbeat`

The notification center HTTP API remains source of truth for reconnect reconciliation.

