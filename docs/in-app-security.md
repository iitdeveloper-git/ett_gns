# In-App Security

Controls:

- Authenticated SSE with bearer tokens in headers.
- Development identity only when dev identity is enabled in development/test.
- Production OIDC validation for issuer, audience, signature, expiry and required scope claims.
- Tenant/application isolation on every user/admin query.
- Safe relative deep links only.
- No arbitrary HTML rendering in SDK components.
- No access tokens in query strings.
- Request IDs and audit events remain available through existing GNS infrastructure.

