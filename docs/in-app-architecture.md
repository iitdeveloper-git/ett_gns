# In-App Architecture

V1 uses SSE as the primary transport because notification delivery is server-to-client and read/dismiss/preference operations are normal HTTP mutations. This keeps infrastructure simple and prepares a future WebSocket transport without creating a separate service.

The implementation remains inside the modular monolith:

- Existing `notifications` rows retain idempotency, event, template and audit context.
- `in_app_notifications` stores rendered durable content.
- `in_app_recipients` stores per-recipient state.
- `in_app_delivery_attempts` records gateway/SDK acknowledgements.
- `in_app_connections` tracks active SSE sessions.
- `in_app_preferences` stores user/event preference overrides.

Local real-time fanout uses an in-process hub. Production horizontal fanout should use Redis pub/sub or Redis Streams.

