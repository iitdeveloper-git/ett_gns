# Send your first notification

After onboarding, call:

```http
POST /api/v1/notifications
Authorization: Bearer gns_<prefix>.<secret>
Idempotency-Key: welcome-001
```

```json
{
  "event_key": "user.welcome",
  "channel": "email",
  "recipient": {"email": "person@example.com"},
  "data": {"name": "Ravi"},
  "metadata": {"correlation_id": "signup-001"}
}
```

`app_id` is optional because GNS derives the application from the credential. If `app_id` is supplied, it must match the credential scope.

