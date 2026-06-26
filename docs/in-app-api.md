# In-App API

Runtime send:

```http
POST /api/v1/notifications
Authorization: Bearer gns_<prefix>.<secret>
Idempotency-Key: payment-pending-INV-1024
```

```json
{
  "event_key": "payment.pending",
  "channel": "in_app",
  "recipient": {"type": "user", "id": "usr_123"},
  "data": {"invoice_id": "INV-1024", "amount": "2500"},
  "priority": 8,
  "metadata": {"deduplication_key": "payment-pending-INV-1024"}
}
```

User APIs:

- `GET /api/v1/in-app/notifications`
- `GET /api/v1/in-app/notifications/{id}`
- `POST /api/v1/in-app/notifications/{id}/ack`
- `POST /api/v1/in-app/notifications/{id}/read`
- `POST /api/v1/in-app/notifications/{id}/unread`
- `POST /api/v1/in-app/notifications/{id}/dismiss`
- `POST /api/v1/in-app/notifications/read-all`
- `GET /api/v1/in-app/unread-count`
- `GET /api/v1/in-app/preferences`
- `PATCH /api/v1/in-app/preferences`

Admin APIs:

- `GET /api/v1/admin/in-app/notifications`
- `POST /api/v1/admin/in-app/test`
- `GET /api/v1/admin/in-app/delivery-attempts`
- `GET /api/v1/admin/in-app/connections`

