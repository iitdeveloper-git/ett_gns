# Testing

Local verified commands:

```bash
ruff format --check .
ruff check .
mypy ett_gns_app
pytest --cov=ett_gns_app --cov-fail-under=75
alembic upgrade head
alembic check
cd admin
npm run lint
npm run typecheck
npm test
npm run build
```

Verified on 2026-06-26: 26 backend tests passed in the restricted suite; its one socket-restricted SMTP test passed separately with loopback permission, so all 27 tests are verified. Scoped backend coverage is 75.54%. Three frontend component tests, one Playwright E2E test, and the production frontend build passed.

CI adds PostgreSQL, RabbitMQ and Redis service containers, migration verification, Playwright, dependency audits, secret scanning, image builds, Trivy and SBOM generation.

Load tests are in `load-tests/`. No performance result is claimed until run against a representative deployment.
