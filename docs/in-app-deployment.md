# In-App Deployment

V1 works in the existing API/worker topology. For a single API instance, the local in-memory SSE hub is enough for development.

For production horizontal scaling:

1. Keep PostgreSQL as source of truth.
2. Add Redis pub/sub or Redis Streams for cross-instance fanout.
3. Route SSE with sticky sessions or shared fanout.
4. Enforce connection limits per user/session.
5. Monitor active connections, replay count, delivery latency and unread backlog.

