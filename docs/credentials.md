# Application credentials

Application credentials are shown once, hashed at rest, scoped by permissions, and may be rotated with overlap or revoked.

Use Swagger Authorize with:

```http
Authorization: Bearer gns_<prefix>.<secret>
```

Never paste credentials into chat, screenshots, logs, tickets, source code, or shell history. Store them in a secret manager.

