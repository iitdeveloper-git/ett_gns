from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from ett_gns_app.delivery import process_notification, reconcile_stuck_notifications
from ett_gns_app.models import DeliveryAttempt, Notification, NotificationStatus, OutboxEvent
from ett_gns_app.settings import Settings
from tests.test_runtime import provision_runtime


def test_worker_records_successful_attempt_and_provider_identifier(
    client: TestClient,
    platform_headers: dict[str, str],
    db: Session,
) -> None:
    application, secret = provision_runtime(client, platform_headers, "delivery-success")
    response = client.post(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {secret}", "Idempotency-Key": "delivery-success"},
        json={
            "app_id": application["id"],
            "event_key": "account.welcome",
            "channel": "email",
            "recipient": {"email": "person@example.com"},
            "data": {"name": "Ravi"},
        },
    )
    assert response.status_code == 202
    notification = process_notification(
        db,
        response.json()["id"],
        Settings(environment="test", api_key_pepper="development-only-change-me"),
    )
    assert notification.status == NotificationStatus.SENT
    attempts = list(
        db.scalars(
            select(DeliveryAttempt).where(DeliveryAttempt.notification_id == notification.id)
        )
    )
    assert len(attempts) == 1
    assert attempts[0].provider_message_id.startswith("fake_")


def test_temporary_failure_defers_then_dead_letters_when_exhausted(
    client: TestClient,
    platform_headers: dict[str, str],
    db: Session,
) -> None:
    application, secret = provision_runtime(client, platform_headers, "delivery-retry")
    response = client.post(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {secret}", "Idempotency-Key": "delivery-retry"},
        json={
            "app_id": application["id"],
            "event_key": "account.welcome",
            "channel": "email",
            "recipient": {"email": "person@example.com"},
            "data": {"name": "Ravi"},
        },
    )
    notification = db.get(Notification, response.json()["id"])
    assert notification is not None
    provider = notification.provider_config_id
    from ett_gns_app.models import ProviderConfig

    provider_record = db.get(ProviderConfig, provider)
    assert provider_record is not None
    provider_record.public_config = {
        **provider_record.public_config,
        "outcome": "temporary_failure",
    }
    db.commit()
    settings = Settings(
        environment="test",
        api_key_pepper="development-only-change-me",
        max_delivery_attempts=2,
    )
    first = process_notification(db, notification.id, settings)
    assert first.status == NotificationStatus.DEFERRED
    assert first.next_attempt_at is not None
    first.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    second = process_notification(db, notification.id, settings)
    assert second.status == NotificationStatus.DEAD_LETTERED
    attempts = list(
        db.scalars(
            select(DeliveryAttempt).where(DeliveryAttempt.notification_id == notification.id)
        )
    )
    assert len(attempts) == 2
    assert all(attempt.retryable for attempt in attempts)


def test_reconciler_recovers_expired_processing_lease(
    client: TestClient,
    platform_headers: dict[str, str],
    db: Session,
) -> None:
    application, secret = provision_runtime(client, platform_headers, "delivery-reconcile")
    response = client.post(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {secret}", "Idempotency-Key": "reconcile"},
        json={
            "app_id": application["id"],
            "event_key": "account.welcome",
            "channel": "email",
            "recipient": {"email": "person@example.com"},
            "data": {"name": "Ravi"},
        },
    )
    notification = db.get(Notification, response.json()["id"])
    assert notification is not None
    notification.status = NotificationStatus.PROCESSING
    notification.processing_lease_until = datetime.now(UTC) - timedelta(seconds=30)
    db.commit()
    recovered = reconcile_stuck_notifications(
        db, Settings(environment="test", api_key_pepper="development-only-change-me")
    )
    assert recovered == 1
    assert notification.status == NotificationStatus.QUEUED
    recovery = db.scalar(
        select(OutboxEvent).where(OutboxEvent.event_type == "notification.lease_recovered")
    )
    assert recovery is not None
