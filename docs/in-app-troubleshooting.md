# In-App Troubleshooting

## No toast appears

Fetch `/api/v1/in-app/notifications` first. If the notification is present there, real-time transport is the issue, not storage.

## Unread count mismatch

Call `/api/v1/in-app/unread-count`; the server response is authoritative. Refresh local SDK state.

## SSE disconnects

Check token expiry, CORS, proxy idle timeout and whether the client sends Authorization in headers.

## Role/group recipients not visible

V1 stores role/group targets and filters by token claims. Full fanout requires IAM membership integration.

