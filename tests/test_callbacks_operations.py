import hashlib
import hmac
import json
import time

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from ett_gns_app.delivery import process_notification
from ett_gns_app.models import DeliveryAttempt, Notification, NotificationStatus
from ett_gns_app.settings import Settings
from tests.test_runtime import provision_runtime


def signed_headers(body: bytes, timestamp: str | None = None) -> dict[str, str]:
    timestamp = timestamp or str(int(time.time()))
    signature = hmac.new(
        b"callback-test-secret", timestamp.encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    return {
        "X-GNS-Callback-Timestamp": timestamp,
        "X-GNS-Callback-Signature": f"v1={signature}",
        "Content-Type": "application/json",
    }


def delivered_notification(
    client: TestClient,
    platform_headers: dict[str, str],
    db: Session,
) -> tuple[Notification, DeliveryAttempt]:
    application, secret = provision_runtime(client, platform_headers, "callbacks")
    response = client.post(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {secret}", "Idempotency-Key": "callback"},
        json={
            "app_id": application["id"],
            "event_key": "account.welcome",
            "channel": "email",
            "recipient": {"email": "person@example.com"},
            "data": {"name": "Ravi"},
        },
    )
    notification = process_notification(
        db,
        response.json()["id"],
        Settings(environment="test", api_key_pepper="development-only-change-me"),
    )
    attempt = db.scalar(
        select(DeliveryAttempt).where(DeliveryAttempt.notification_id == notification.id)
    )
    assert attempt is not None
    return notification, attempt


def test_callback_signature_replay_idempotency_and_delivery_transition(
    client: TestClient,
    platform_headers: dict[str, str],
    db: Session,
) -> None:
    notification, attempt = delivered_notification(client, platform_headers, db)
    payload = {
        "event_id": "provider-event-1",
        "message_id": attempt.provider_message_id,
        "status": "delivered",
    }
    body = json.dumps(payload, separators=(",", ":")).encode()
    path = f"/api/v1/callbacks/{notification.provider_config_id}"
    accepted = client.post(path, content=body, headers=signed_headers(body))
    assert accepted.status_code == 202, accepted.text
    assert accepted.json()["duplicate"] is False
    db.refresh(notification)
    assert notification.status == NotificationStatus.DELIVERED
    duplicate = client.post(path, content=body, headers=signed_headers(body))
    assert duplicate.status_code == 202
    assert duplicate.json()["duplicate"] is True
    forged = client.post(
        path,
        content=body,
        headers={
            "X-GNS-Callback-Timestamp": str(int(time.time())),
            "X-GNS-Callback-Signature": "v1=forged",
        },
    )
    assert forged.status_code == 401
    old_timestamp = str(int(time.time()) - 1000)
    stale = client.post(path, content=body, headers=signed_headers(body, old_timestamp))
    assert stale.status_code == 401


def test_operations_timeline_redacts_recipient_and_operator_can_retry(
    client: TestClient,
    platform_headers: dict[str, str],
    db: Session,
) -> None:
    notification, _ = delivered_notification(client, platform_headers, db)
    notification.status = NotificationStatus.FAILED
    db.commit()
    tenant_id = notification.tenant_id
    operator_headers = {
        "X-Admin-User": "operator",
        "X-Admin-Roles": "operations_operator",
        "X-Tenant-ID": tenant_id,
    }
    timeline = client.get(
        f"/api/v1/operations/notifications/{notification.id}",
        headers=operator_headers,
    )
    assert timeline.status_code == 200
    assert timeline.json()["recipient"]["email"] == "***"
    retried = client.post(
        f"/api/v1/operations/notifications/{notification.id}/retry",
        headers=operator_headers,
    )
    assert retried.status_code == 200
    assert retried.json()["status"] == "queued"
