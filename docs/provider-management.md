# Provider management

Provider secrets are write-only. Use `secret_config`, for example:

```json
{"password": "smtp-password"}
```

Main endpoints:

- `POST /api/v1/provider-configs/test-connection`
- `GET /api/v1/provider-configs/{provider_id}`
- `PATCH /api/v1/provider-configs/{provider_id}`
- `POST /api/v1/provider-configs/{provider_id}/replace-secret`
- `POST /api/v1/provider-configs/{provider_id}/test`
- `POST /api/v1/provider-configs/{provider_id}/activate`
- `POST /api/v1/provider-configs/{provider_id}/deactivate`
- `POST /api/v1/provider-configs/{provider_id}/set-default`
- `POST /api/v1/provider-configs/{provider_id}/unset-default`
- `DELETE /api/v1/provider-configs/{provider_id}`

Activation requires `healthy`. Archive requires inactive and non-default; it removes fallback dependencies and destroys secret material while preserving historical notification references.

