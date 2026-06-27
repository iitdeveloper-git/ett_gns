# Execution Plan

Last updated: 2026-06-28

All locally executable GNS Core stabilization implementation and verification work is complete.

Resume in this order when external systems are available:

1. URL-encode reserved characters in the external `GNS_DATABASE_URL` password.
2. Execute the Docker procedure in `docs/local-development.md`.
3. Verify PostgreSQL migrations, SMTP through Mailpit, temporary retry, permanent DLQ and replay.
4. Configure sandbox credentials for SMS, push, Telegram, WhatsApp and public webhooks.
5. Configure an OIDC test realm and verify every documented role.
6. Deploy `render.yaml` or the chosen managed-container equivalent to staging.
7. Run DAST and the k6 scenarios; record real latency, throughput, queue age and sizing.
8. Validate in-app SSE with Redis pub/sub or streams in a multi-instance staging topology.
9. Integrate IAM role/group membership expansion for in-app fan-out.
10. Complete the release checklist and production approval.
