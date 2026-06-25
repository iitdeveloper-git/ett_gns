from __future__ import annotations

from datetime import UTC, datetime, timedelta
from time import perf_counter

from prometheus_client import Counter, Histogram
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ett_gns_app.channels import AdapterError, adapter_for
from ett_gns_app.models import (
    Application,
    DeliveryAttempt,
    DeliveryEvent,
    Notification,
    NotificationStatus,
    OutboxEvent,
    ProviderConfig,
    Template,
    TemplateVersion,
)
from ett_gns_app.resolution import resolve_email_sender
from ett_gns_app.secrets import SecretStore
from ett_gns_app.settings import Settings
from ett_gns_app.template_service import render_content

RETRY_DELAYS_SECONDS = [60, 300, 1800, 7200, 28800, 86400]
DELIVERY_RESULTS = Counter(
    "gns_delivery_results_total",
    "Normalized delivery results",
    ["channel", "provider_type", "result"],
)
PROVIDER_LATENCY = Histogram(
    "gns_provider_duration_seconds",
    "Provider call duration",
    ["channel", "provider_type"],
)


class LeaseUnavailable(RuntimeError):
    pass


def aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=value.tzinfo or UTC)


def process_notification(db: Session, notification_id: str, settings: Settings) -> Notification:
    now = datetime.now(UTC)
    notification = db.get(Notification, notification_id)
    if not notification:
        raise ValueError("Notification not found")
    if notification.status in {
        NotificationStatus.CANCELLED,
        NotificationStatus.SENT,
        NotificationStatus.DELIVERED,
        NotificationStatus.FAILED,
        NotificationStatus.DEAD_LETTERED,
    }:
        return notification
    scheduled_at = aware(notification.scheduled_at)
    next_attempt_at = aware(notification.next_attempt_at)
    lease_until = aware(notification.processing_lease_until)
    if scheduled_at and scheduled_at > now:
        return notification
    if next_attempt_at and next_attempt_at > now:
        return notification
    if notification.status == NotificationStatus.PROCESSING and lease_until and lease_until > now:
        raise LeaseUnavailable("Notification already has an active processing lease")
    notification.status = NotificationStatus.PROCESSING
    notification.processing_lease_until = now + timedelta(seconds=settings.processing_lease_seconds)
    db.commit()

    app = db.get(Application, notification.application_id)
    version = db.get(TemplateVersion, notification.template_version_id)
    provider = db.get(ProviderConfig, notification.provider_config_id)
    if not app or not version or not provider:
        notification.status = NotificationStatus.FAILED
        notification.failure_code = "SNAPSHOT_MISSING"
        notification.processing_lease_until = None
        db.commit()
        return notification
    template = db.get(Template, version.template_id)
    if not template:
        notification.status = NotificationStatus.FAILED
        notification.failure_code = "TEMPLATE_MISSING"
        notification.processing_lease_until = None
        db.commit()
        return notification
    attempt_number = (
        db.scalar(
            select(func.count())
            .select_from(DeliveryAttempt)
            .where(DeliveryAttempt.notification_id == notification.id)
        )
        or 0
    ) + 1
    started = perf_counter()
    try:
        content = render_content(version.content, notification.event_data)
        secret = SecretStore(settings).decrypt(provider.secret_ciphertext)
        sender = resolve_email_sender(app, provider) if notification.channel == "email" else {}
        adapter = adapter_for(notification.channel, provider.provider_type)
        result = adapter.send(
            provider.public_config,
            secret,
            sender,
            notification.recipient,
            content,
            notification.metadata_json,
        )
        PROVIDER_LATENCY.labels(notification.channel, provider.provider_type).observe(
            perf_counter() - started
        )
        DELIVERY_RESULTS.labels(notification.channel, provider.provider_type, result.status).inc()
        attempt = DeliveryAttempt(
            tenant_id=notification.tenant_id,
            notification_id=notification.id,
            attempt_number=attempt_number,
            provider_config_id=provider.id,
            status=result.status,
            retryable=False,
            provider_message_id=result.provider_message_id,
            response_excerpt=result.response_excerpt,
            duration_ms=round((perf_counter() - started) * 1000),
        )
        db.add(attempt)
        db.flush()
        db.add(
            DeliveryEvent(
                tenant_id=notification.tenant_id,
                notification_id=notification.id,
                provider_config_id=provider.id,
                provider_event_id=f"internal:{attempt.id}",
                status="provider_accepted",
                occurred_at=datetime.now(UTC),
                raw_payload=None,
            )
        )
        notification.status = NotificationStatus.SENT
        notification.failure_code = None
        notification.next_attempt_at = None
    except AdapterError as exc:
        PROVIDER_LATENCY.labels(notification.channel, provider.provider_type).observe(
            perf_counter() - started
        )
        DELIVERY_RESULTS.labels(
            notification.channel,
            provider.provider_type,
            "retry" if exc.retryable else "failed",
        ).inc()
        db.add(
            DeliveryAttempt(
                tenant_id=notification.tenant_id,
                notification_id=notification.id,
                attempt_number=attempt_number,
                provider_config_id=provider.id,
                status="failed",
                retryable=exc.retryable,
                error_code=exc.code,
                error_message=str(exc)[:2000],
                duration_ms=round((perf_counter() - started) * 1000),
            )
        )
        notification.failure_code = exc.code
        if exc.retryable and attempt_number < settings.max_delivery_attempts:
            notification.status = NotificationStatus.DEFERRED
            delay_index = min(attempt_number - 1, len(RETRY_DELAYS_SECONDS) - 1)
            notification.next_attempt_at = datetime.now(UTC) + timedelta(
                seconds=RETRY_DELAYS_SECONDS[delay_index]
            )
            db.add(
                OutboxEvent(
                    tenant_id=notification.tenant_id,
                    aggregate_type="notification",
                    aggregate_id=notification.id,
                    event_type="notification.retry_scheduled",
                    payload={
                        "notification_id": notification.id,
                        "available_at": notification.next_attempt_at.isoformat(),
                    },
                )
            )
        elif exc.retryable:
            notification.status = NotificationStatus.DEAD_LETTERED
        else:
            notification.status = NotificationStatus.FAILED
    except Exception as exc:
        db.add(
            DeliveryAttempt(
                tenant_id=notification.tenant_id,
                notification_id=notification.id,
                attempt_number=attempt_number,
                provider_config_id=provider.id,
                status="failed",
                retryable=False,
                error_code="INTERNAL_DELIVERY_ERROR",
                error_message=str(exc)[:2000],
                duration_ms=round((perf_counter() - started) * 1000),
            )
        )
        notification.status = NotificationStatus.FAILED
        notification.failure_code = "INTERNAL_DELIVERY_ERROR"
    notification.processing_lease_until = None
    db.commit()
    return notification


def reconcile_stuck_notifications(db: Session, settings: Settings) -> int:
    now = datetime.now(UTC)
    stuck = list(
        db.scalars(
            select(Notification).where(
                Notification.status == NotificationStatus.PROCESSING,
                Notification.processing_lease_until < now,
            )
        )
    )
    for notification in stuck:
        notification.status = NotificationStatus.QUEUED
        notification.processing_lease_until = None
        db.add(
            OutboxEvent(
                tenant_id=notification.tenant_id,
                aggregate_type="notification",
                aggregate_id=notification.id,
                event_type="notification.lease_recovered",
                payload={"notification_id": notification.id},
            )
        )
    db.commit()
    return len(stuck)
