# In-App Notifications Implementation Matrix

Last updated: 2026-06-26

| Requirement | Current state before work | Implementation plan | Evidence target | External blocker |
|---|---|---|---|---|
| `in_app` channel | Missing | Add to schemas, template validation, runtime acceptance | Backend tests | None |
| Durable in-app records | Missing | Add `in_app_notifications`, recipients, preferences, delivery attempts, connections | Alembic + model tests | None |
| User targeting | Missing | Support `user`, `users`, `role`, `group`, `tenant`, `application` recipient shapes with tenant/app isolation | API tests | IAM role/group expansion external |
| SSE transport | Missing | Add authenticated `/api/v1/in-app/stream` with ready, heartbeat, replay and in-memory local hub | Integration tests | Horizontal Redis pub/sub validation |
| Offline/reconnect | Missing | Notification center is source of truth; SSE replays unread/missed by Last-Event-ID | Integration tests | None |
| Read/unread/dismiss/ack | Missing | User APIs mutate recipient timestamps and publish update events | API tests | None |
| Preferences | Missing | Store per-user/app/event preferences with priority gates | API tests | IAM/application policy external |
| SDK and UI | Missing | Add headless/styled React package plus demo Next.js page | Type/build checks | None |
| Admin visibility/test | Missing | Add admin APIs and admin console section | Backend/frontend checks | None |
| Security | Missing for in-app | Dev-only user token boundary; production OIDC validation; no query tokens; safe deep links | Tests/docs | Live OIDC provider |
| Load tests | Missing | Add runnable k6 scenario artifacts | File checks | k6 unavailable locally |
| Existing channels | Passing | Keep regression suite green | Existing backend tests | None |

