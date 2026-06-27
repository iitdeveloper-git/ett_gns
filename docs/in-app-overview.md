# In-App Notifications Overview

GNS now supports `in_app` as a first-class channel. A toast is only presentation; the durable source of truth is the in-app notification center.

Flow:

1. Application sends `POST /api/v1/notifications` with `channel: "in_app"`.
2. GNS validates credential, event schema, template and idempotency.
3. Worker renders the in-app template.
4. GNS stores `in_app_notifications` and `in_app_recipients`.
5. Connected users receive SSE events.
6. Users fetch notification center state, acknowledge display/open, read/unread, dismiss, and manage preferences through HTTP APIs.

