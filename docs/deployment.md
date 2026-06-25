# Deployment

## Profiles

- Local: Compose with PostgreSQL, RabbitMQ, Redis and Mailpit.
- CI: GitHub service containers and deterministic fake providers.
- Staging: `render.yaml` or equivalent managed containers; real sandbox providers.
- Production: immutable images, managed PostgreSQL/RabbitMQ/Redis, OIDC and cloud secret manager.

Run migrations as a one-shot job before API/workers. Use expand/migrate/contract changes: deploy backward-compatible schema, deploy code, backfill, then remove old fields in a later release.

Health probes:

- `/health/live`: process liveness
- `/health/ready`: database readiness
- `/health/dependencies`: database, Redis and broker diagnosis

Back up PostgreSQL with daily snapshots plus point-in-time recovery. Test restore quarterly. RabbitMQ is transport, not the source of truth; unpublished outbox rows are recoverable.

Rollback uses the previous immutable image. Do not downgrade a destructive migration; deploy a forward corrective migration. Published template rollback is independent through the management API.

The provided Render blueprint expects an external managed AMQP URL. Staging deployment is externally blocked until a target and credentials are supplied.
