# Operations

## Provider outage

Confirm provider health/error metrics, stop activation of bad credentials, open the circuit, and activate only an explicitly approved secondary. Replay deferred/DLQ notifications after recovery.

## Queue backlog

Check queue depth/age, database latency and provider throttling. Scale the affected worker queue, throttle noisy apps and use reconciliation for expired leases.

## Credential compromise

Revoke the application key, rotate with zero overlap, replace provider secrets, review audit events and suspend the application if abuse is suspected.

## Bad template

Deprecate the bad version, roll back to a prior published version, identify affected notifications and record the operator action.

## Data retention

Expire raw callback payloads according to `GNS_CALLBACK_RAW_RETENTION_DAYS`. Retain normalized delivery/audit records according to legal and contractual policy.

Import `observability/grafana-dashboard.json` into Grafana. Alert on queue age, provider error spikes, DLQ growth, callback signature failures and database saturation.
