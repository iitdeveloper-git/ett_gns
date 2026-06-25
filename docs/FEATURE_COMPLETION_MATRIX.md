# GNS Feature Completion Matrix

Last audited: 2026-06-26

Status vocabulary: `implemented and verified`, `implemented but unverified`, `partial`, `mock only`, `missing`, `externally blocked`.

The continuation brief referenced commits `cc44128` and `fdfbcca`; neither exists in this checkout. This matrix reports only the implementation and verification present here.

| Requirement | Current status | Implementation files | Tests | Remaining work | External dependency, if any |
|---|---|---|---|---|---|
| Tenants | implemented and verified | `models.py`, `api.py` | CRUD/lifecycle/isolation | PostgreSQL concurrency validation | Docker/PostgreSQL |
| Applications | implemented and verified | `models.py`, `api.py` | CRUD/lifecycle/isolation | Branding editor depth | None |
| Credentials | implemented and verified | `security.py`, `api.py` | one-time reveal/hash/expiry/last-use | Cloud secret-manager operations | Cloud secret manager |
| API-key rotation and revocation | implemented and verified | `security.py`, `api.py` | overlap/zero-overlap/revoke | Concurrent overlap test on PostgreSQL | PostgreSQL |
| Admin RBAC | implemented and verified | `security.py` | tenant role/permission denial | More frontend role-specific component tests | Live OIDC |
| OIDC boundary | implemented but unverified | `security.py`, `settings.py` | production safety logic | Live discovery/JWKS/claim verification | OIDC provider |
| Events | implemented and verified | `api.py`, `models.py` | create/list/update/disable | Recipient-policy UI editor | None |
| Schema versions and compatibility | implemented and verified | `api.py` | valid, compatible and incompatible revisions | Broader JSON Schema compatibility semantics | None |
| Templates | implemented and verified | `management_api.py`, `template_service.py` | lifecycle/security tests | Channel-specific authoring polish | None |
| Preview | implemented and verified | `management_api.py`, admin templates page | render tests | Rich iframe email preview | None |
| Test send | implemented and verified | `management_api.py` | deterministic fake test send | Live-provider test sends | Provider credentials |
| Publish | implemented and verified | `management_api.py` | validation gate/immutability | None | None |
| Rollback | implemented and verified | `management_api.py` | prior published version rollback | None | None |
| Localization | implemented and verified | `resolution.py` | resolution exercised by runtime | Translation workflow/import | None |
| Variants | implemented and verified | `resolution.py`, `models.py` | default resolution | Weighted experiment allocation | None |
| Providers | implemented and verified | `management_api.py`, `secrets.py` | CRUD/masking/lifecycle | Cloud secret-store adapter | Cloud secret manager |
| Provider verification | partial | `management_api.py`, `SMTPAdapter` | config/fake and SMTP connection code | Live connectivity for every provider | Provider credentials |
| App-specific providers | implemented and verified | `resolution.py` | app provider wins | Live sender-domain verification | Provider credentials/DNS |
| Default providers | implemented and verified | `resolution.py` | policy/sender tests | Platform-global scope beyond tenant default | None |
| Fallback policies | implemented and verified | `resolution.py`, provider APIs | explicit secondary and auth-failure prohibition | Live failover drill | Provider credentials |
| Notifications | implemented and verified | `api.py`, `models.py` | durable acceptance/status | Full PostgreSQL/RabbitMQ E2E | Docker |
| Idempotency | implemented and verified | `api.py` | duplicate/conflict | Concurrent PostgreSQL race test | PostgreSQL |
| Outbox | implemented and verified | `models.py`, `tasks.py` | transaction/recovery model tests | RabbitMQ publication integration | Docker/RabbitMQ |
| Workers | implemented but unverified | `delivery.py`, `tasks.py` | direct worker service tests | Live Celery/RabbitMQ execution | Docker/RabbitMQ |
| Retries | implemented and verified | `delivery.py` | temporary failure schedule/exhaustion | Broker ETA integration | RabbitMQ |
| DLQ | implemented and verified | `delivery.py`, `operations_api.py` | exhaustion and replay APIs | Queue-level DLQ integration | RabbitMQ |
| Scheduling | implemented and verified | `api.py`, `tasks.py` | scheduled persistence, outbox ETA and worker guard | Broker ETA integration | RabbitMQ |
| Cancellation | implemented and verified | `api.py` | legal pre-processing cancellation | Race test with live worker | RabbitMQ |
| Callbacks | implemented and verified | `callbacks.py` | signature/replay/idempotency | Provider-specific live formats | Provider credentials |
| Delivery receipts | implemented and verified | `callbacks.py` | normalized legal transitions | Live receipt delivery | Provider callbacks |
| Email | implemented and verified | `SMTPAdapter` | local SMTP text/HTML integration, attachments/errors | Live SSL/STARTTLS provider | SMTP credentials |
| SMS | implemented but unverified | `JSONAPIAdapter` | Twilio mock contract/E.164 | Live Twilio sandbox | Credentials |
| Webhooks | implemented and verified | `WebhookAdapter` | HMAC/SSRF/mock contract | Public live destination | External endpoint |
| Push | implemented but unverified | `JSONAPIAdapter` | FCM mock contract | Live FCM | Credentials |
| Telegram | implemented but unverified | `JSONAPIAdapter` | Bot API mock contract | Media endpoint/live bot | Bot token |
| WhatsApp | implemented but unverified | `JSONAPIAdapter` | Meta mock contract | Live approved templates/callback formats | Meta credentials |
| Quotas | implemented and verified | `quotas.py` | minute/day/duplicate behavior | PostgreSQL concurrency stress | PostgreSQL |
| Usage metering | implemented and verified | `UsageBucket` | quota usage test | Reporting/export API depth | None |
| Audits | implemented and verified | `AuditEvent`, APIs/admin | control-plane assertions | External immutable archive | Log/archive backend |
| Logs | implemented and verified | `main.py` | runtime observation | Central log ingestion | Deployment |
| Metrics | implemented and verified | `main.py`, `delivery.py` | endpoint/runtime observation | Broker queue exporter | Metrics backend |
| Tracing | implemented but unverified | `observability.py`, `main.py` | manual API + SQL instrumentation import | Collector/export and worker propagation | OTLP backend |
| Admin console | implemented and verified | `admin/` | lint/type/unit/build/browser desktop+mobile | Live OIDC and expanded component/E2E suite | OIDC |
| CI/CD | implemented but unverified | `.github/workflows/` | local equivalent gates pass | Execute workflows in GitHub | GitHub environments/secrets |
| Deployment | externally blocked | Dockerfiles, Compose, `render.yaml`, docs | migrations local only | Build/run Compose and deploy staging | Docker/cloud target |
| Security testing | implemented and verified | security/API/adapter tests, verification doc | automated tests and audits | Staging DAST/WAF/IAM review | Staging |
| Load testing | externally blocked | `load-tests/` | scripts reviewed only | Run and record measurements | Representative deployment |
| Operations documentation | implemented and verified | `docs/operations.md`, troubleshooting, Grafana JSON | documentation review | Deployment-specific ownership/contacts | Operator input |

## Verified quality state

- Backend: 26 pass in the restricted suite; the one socket-restricted SMTP test also passes when run with loopback permission (all 27 verified).
- Scoped backend coverage: 75.54%.
- Ruff formatting/lint: pass.
- Strict mypy: pass for the production FastAPI code; retained legacy Flask migration files are explicitly excluded.
- Alembic upgrade/check: pass with no drift.
- Frontend lint/type/unit/build: pass; three component tests.
- Browser QA: desktop and mobile layouts, API integration, empty states, modal, workspace persistence; no console warnings.
- Python audit: no known vulnerabilities.
- npm audit: zero vulnerabilities.
- Docker: unavailable, so no image/Compose claim.
- Live providers, OIDC, load test and staging: externally blocked.
