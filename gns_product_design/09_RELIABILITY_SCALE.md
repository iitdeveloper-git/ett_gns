# Reliability and Scale

## Delivery model

At-least-once internal delivery with idempotency. Exactly-once external delivery is not guaranteed.

## Queue topology

```text
email.main
sms.main
webhook.main
push.main
whatsapp.main
telegram.main
retry.delay
dead_letter
callback.events
```

## Retry example

```text
0 min -> 1 min -> 5 min -> 30 min -> 2 hr -> 8 hr
```

Use exponential backoff with jitter.

## Transactional outbox

Insert notification and outbox event in the same transaction. A publisher moves outbox events to the queue.

## Circuit breaker

Per provider:

- closed
- open
- half-open

## Noisy-neighbor controls

- per-tenant limits
- fair scheduling
- worker concurrency caps
- channel queue isolation
- provider quota awareness

## High-scale evolution

- Stateless API replicas
- Channel-specific worker pools
- Database read replicas
- Table partitioning
- Regional queues
- Tenant home region
- Dedicated enterprise queues
