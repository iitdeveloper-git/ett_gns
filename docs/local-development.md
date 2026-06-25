# Local development

## Native

1. Use Python 3.12+ and Node 22.
2. Copy `sample.env` to `.env` and replace both development secret values.
3. Install `requirements-dev.txt`.
4. Run `alembic upgrade head`.
5. Start `uvicorn ett_gns_app.main:app --reload --port 5000`.
6. In `admin/`, run `npm ci && npm run dev`.

SQLite is supported only for deterministic local tests and development. PostgreSQL is required for staging/production.

## Compose

```bash
docker compose build
docker compose up
```

Services: PostgreSQL, RabbitMQ, Redis, Mailpit, migration job, API, outbox publisher, worker, scheduler and admin. Mailpit is at `http://localhost:8025`.

The current Codex environment had no Docker executable, so these commands are documented but not claimed as executed.

## Development identity

Development identity mode is permitted only when `GNS_ENVIRONMENT` is `development` or `test`. Production settings validation rejects it.
