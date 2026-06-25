# Observability and Operations

## Structured logs

Include:

```text
request_id
correlation_id
tenant_id
application_id
notification_id
event_key
channel
provider
attempt_number
status
duration_ms
error_code
```

## Metrics

- API rate/errors/latency
- Queue depth/age
- Success/retry/DLQ rate
- Provider latency/error rate
- Bounce/complaint rate
- Template rendering failures
- Per-tenant usage

## Tracing

Trace from API request through outbox, queue, worker, provider, and callback.

## Alerts

- Queue age high
- Provider failure spike
- DLQ growth
- DB saturation
- Callback signature failures
- Tenant abuse
- Bounce/complaint threshold

## Runbooks

### Provider outage
Open circuit, pause affected queue, enable approved secondary provider, replay deferred work.

### Credential compromise
Revoke key, rotate provider secrets, review audit logs, suspend app if abused.

### Bad template
Deprecate, rollback, inspect affected sends, audit action.

### Queue backlog
Scale workers, identify bottleneck, throttle noisy tenant, prioritize critical traffic.
