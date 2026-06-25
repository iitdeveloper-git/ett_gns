# Security design

- Tenant identity comes from verified human or application credentials, never request-body trust.
- API key secrets use scrypt with random salt and a deployment pepper; only hashes are stored.
- Provider secrets are encrypted behind a replaceable secret-store boundary and never returned.
- Development identity is rejected by production configuration validation.
- Published templates are sandboxed, autoescaped and HTML-sanitized.
- Webhook destinations require HTTPS and reject loopback, private, link-local, reserved and metadata networks after DNS resolution.
- Webhooks and callbacks use timestamped HMAC signatures and replay windows.
- Callback event IDs are unique per provider.
- Request size, schema, recipient, quota and sender rules are enforced before acceptance.
- Logs and metrics avoid recipient data and high-cardinality tenant labels.
- CORS is an explicit origin allowlist.

TLS, WAF, managed-secret IAM, database encryption, provider DNS records and network egress controls remain deployment responsibilities.
