# Provider development

Provider records store public configuration and encrypted secret ciphertext separately. API reads expose only `secret_configured`.

Selection rules:

1. active healthy app provider
2. if any app provider exists but none is healthy, fail
3. otherwise an active healthy tenant default with `default_if_absent`
4. otherwise fail

Authentication failures never silently change sender or brand. Explicit secondary failover requires a future policy record identifying the approved secondary; it is not inferred.

Default SMTP always uses its authenticated `from_email`. App branding may change the display name only when enabled. Reply-To is included only when present in `verified_reply_to`.
