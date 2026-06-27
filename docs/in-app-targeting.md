# In-App Targeting

Supported request recipients:

- `{"type":"user","id":"usr_123"}`
- `{"type":"users","ids":["usr_123","usr_456"]}`
- `{"type":"role","id":"doctor"}`
- `{"type":"group","id":"finance-team"}`
- `{"type":"tenant"}`
- `{"type":"application"}`

User, tenant and application visibility are enforced by token claims. Role/group fanout is stored durably but full membership expansion is an IAM integration point.

