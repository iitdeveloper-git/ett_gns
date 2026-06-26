# Deployment Status

Last checked: 2026-06-26

| Check | Result |
|---|---|
| Docker executable | Blocked: `docker: command not found` |
| Compose build/up | Not run because Docker is unavailable |
| Alembic upgrade/check/downgrade | Pass on SQLite deterministic profile |
| API local startup | Pass on `127.0.0.1:5000` |
| Admin local startup/browser integration | Pass on `127.0.0.1:3000` |
| Local SMTP integration | Pass with loopback socket permission |
| Celery/RabbitMQ/Redis integration | Artifacts complete; Docker blocked |
| Python dependency audit | Pass: no known vulnerabilities |
| npm dependency audit | Pass: zero vulnerabilities |
| Live provider delivery | Blocked: credentials unavailable |
| Live OIDC login | Blocked: provider unavailable |
| Staging deployment | Blocked: target and cloud permissions unavailable |
| Load results | Blocked: `k6: command not found` and representative deployment unavailable |
