# GNS Core Security Verification

Last updated: 2026-06-28

| Control | Verification | Status |
|---|---|---|
| Cross-tenant denial | Tenant admin cannot read another tenant app | Pass |
| Cross-application denial | Application credential mismatch returns `application_scope_mismatch` | Pass |
| Invalid role rejection | Unknown/no dev roles rejected | Pass |
| API-key hashing | Scrypt hash and one-time secret reveal only | Pass |
| API-key revocation/rotation | Rotate with overlap and revoke covered by tests/UI | Pass |
| Secret encryption | Provider secrets encrypted through `SecretStore` | Pass |
| Secret masking | Provider read/list/test responses never include secret values | Pass |
| No secrets in pre-save test | Pre-save connection test audits only `secret_supplied` | Pass |
| Provider test rate limit | In-memory per principal/client limiter present | Pass |
| Password write-only behavior | SMTP password accepted as `secret_config.password` and never returned | Pass |
| Template sandbox | Strict Jinja sandbox and HTML sanitation | Pass |
| Webhook SSRF | Adapter rejects local/private unsafe destinations | Pass |
| Callback forgery/replay | HMAC timestamp and replay/idempotency tests | Pass |
| Idempotency conflict | Same key/different payload returns conflict | Pass |
| CORS | Explicit localhost admin origins and auth headers | Pass |
| Dev identity production safety | Settings reject `ALLOW_DEV_IDENTITY=true` in production | Pass |
| Stale local-storage recovery | Selectors clear missing tenant/app IDs | Pass |
| Provider archive dependency checks | Active/default providers blocked; fallback dependencies cleared; secret material destroyed | Pass |

External verification still required: live OIDC role/scope claims, live provider sandboxes, Docker Compose PostgreSQL/queue integration, staging DAST, and production network policy review.
