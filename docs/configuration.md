# Configuration

All backend settings use the `GNS_` prefix.

| Setting | Purpose |
|---|---|
| `GNS_ENVIRONMENT` | development, test, staging or production |
| `GNS_DATABASE_URL` | SQLAlchemy URL; PostgreSQL required in production |
| `GNS_BROKER_URL` | RabbitMQ/AMQP broker |
| `GNS_RESULT_BACKEND_URL` | Redis URL |
| `GNS_ALLOW_DEV_IDENTITY` | must be false in production |
| `GNS_API_KEY_PEPPER` | API-key hashing pepper |
| `GNS_PROVIDER_SECRET_KEY` | provider-secret encryption key |
| `GNS_OIDC_ISSUER` / `GNS_OIDC_AUDIENCE` | production human identity |
| `GNS_CORS_ORIGINS` | explicit admin-console origins |
| `GNS_MAX_REQUEST_BYTES` | API/callback payload cap |
| `GNS_CALLBACK_REPLAY_WINDOW_SECONDS` | callback timestamp tolerance |
| `GNS_CALLBACK_RAW_RETENTION_DAYS` | raw callback retention |
| `GNS_PROCESSING_LEASE_SECONDS` | worker lease duration |
| `GNS_MAX_DELIVERY_ATTEMPTS` | retry ceiling |

Use a cloud secret manager for production values. Never commit `.env`.
