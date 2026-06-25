# Security verification

Last run: 2026-06-26

| Control | Verification | Result |
|---|---|---|
| Cross-tenant denial | API tests access an unrelated app with tenant-admin identity | Pass |
| API-key hashing/one-time reveal | Credential creation/list/rotation/revocation tests | Pass |
| Secret masking/encryption | Provider API tests and `SecretStore` | Pass |
| Template sandbox/variable allowlist | unsafe construct and unknown variable tests | Pass |
| HTML sanitization | script element rejection test | Pass |
| Webhook SSRF | private/loopback resolution test | Pass |
| Webhook HMAC | signed mock-transport contract test | Pass |
| Callback forgery/replay | forged signature, stale timestamp and duplicate tests | Pass |
| Idempotency conflict | duplicate and changed-body tests | Pass |
| Quota bypass | duplicate-not-charged and unique-request rejection test | Pass |
| Dangerous attachment | path/type rejection test | Pass |
| Sender integrity | authenticated From and verified Reply-To unit test | Pass |
| SMTP integration | loopback SMTP server with text/HTML alternatives | Pass |
| Production configuration | settings validator rejects dev identity/default secrets/non-PostgreSQL | Implemented; deployment verification pending |
| Python dependencies | `pip-audit -r requirements.txt` | No known vulnerabilities |
| Frontend dependencies | `npm audit` | Zero vulnerabilities |

External verification still required: live OIDC, cloud secret-manager IAM, WAF/egress policy, DKIM/SPF/DMARC, DAST against staging and cloud audit retention.
