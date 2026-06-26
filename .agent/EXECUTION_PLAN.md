# Execution Plan

Last updated: 2026-06-26

All locally executable GNS Core stabilization implementation and verification work is complete.

Resume in this order when external systems are available:

1. Execute the Docker procedure in `docs/local-development.md`.
2. Verify PostgreSQL migrations, SMTP through Mailpit, temporary retry, permanent DLQ and replay.
3. Configure sandbox credentials for SMS, push, Telegram, WhatsApp and public webhooks.
4. Configure an OIDC test realm and verify every documented role.
5. Deploy `render.yaml` or the chosen managed-container equivalent to staging.
6. Run DAST and the k6 scenarios; record real latency, throughput, queue age and sizing.
7. Complete the release checklist and production approval.
