# Troubleshooting

- `idempotency_conflict`: the same key was used with different request content.
- `app_provider_unavailable`: an app provider exists but is inactive/unhealthy; fix it instead of relying on default fallback.
- `template_not_found`: publish the matching channel/locale/variant or configure locale fallback.
- `provider_not_verified`: test the provider before activation.
- `callback_signature_invalid`: compare raw body, timestamp and callback secret; do not parse/re-encode before HMAC verification.
- Stuck `processing`: run `python -m ett_gns_app.cli reconcile`; verify lease clocks.
- Outbox backlog: run the outbox process, check RabbitMQ and inspect `last_error`.
- Admin `Failed to fetch`: verify API URL, CORS origin and `/health/ready`.
- Migration drift: run `alembic check`; create a reviewed revision instead of editing a released migration.
