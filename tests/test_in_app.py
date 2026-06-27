from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from ett_gns_app.delivery import process_notification
from ett_gns_app.models import InAppNotification, InAppRecipient, Notification
from ett_gns_app.settings import get_settings
from tests.test_control_plane import create_tenant_and_app


def provision_in_app(
    client: TestClient, platform_headers: dict[str, str], suffix: str = "in-app"
) -> tuple[dict, str, dict[str, str]]:
    tenant, application = create_tenant_and_app(client, platform_headers, suffix)
    admin = {
        "X-Admin-User": "tenant-admin",
        "X-Admin-Roles": "tenant_admin",
        "X-Tenant-ID": tenant["id"],
    }
    event = client.post(
        f"/api/v1/apps/{application['id']}/events",
        headers=admin,
        json={
            "event_key": "payment.pending",
            "allowed_channels": ["in_app"],
            "schema": {
                "type": "object",
                "required": ["invoice_id", "amount"],
                "properties": {
                    "invoice_id": {"type": "string"},
                    "amount": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
    )
    assert event.status_code == 201, event.text
    template = client.post(
        f"/api/v1/apps/{application['id']}/events/payment.pending/templates",
        headers=admin,
        json={
            "channel": "in_app",
            "locale": "en",
            "content": {
                "title": "Payment pending",
                "message": "Invoice {{ invoice_id }} for {{ amount }} is still unpaid.",
                "severity": "warning",
                "action": {
                    "label": "View invoice",
                    "url": "/invoices/{{ invoice_id }}",
                    "type": "deep_link",
                },
                "toast": {"enabled": True, "auto_dismiss_ms": 6000},
            },
            "sample_data": {"invoice_id": "INV-1024", "amount": "2500"},
        },
    )
    assert template.status_code == 201, template.text
    assert client.post(f"/api/v1/template-versions/{template.json()['id']}/validate", headers=admin).status_code == 200
    assert client.post(f"/api/v1/template-versions/{template.json()['id']}/publish", headers=admin).status_code == 200
    credential = client.post(
        f"/api/v1/apps/{application['id']}/credentials",
        headers=admin,
        json={"name": "in-app", "permissions": ["notifications:send", "notifications:read"]},
    )
    assert credential.status_code == 201
    return application, credential.json()["secret"], admin


def user_headers(application: dict, user_id: str = "usr_123") -> dict[str, str]:
    return {
        "Authorization": f"Bearer dev_user_{user_id}",
        "X-Tenant-ID": application["tenant_id"],
        "X-App-ID": application["id"],
        "X-Session-ID": "ses_test",
    }


def test_in_app_notification_center_read_dismiss_and_preferences(
    client: TestClient, platform_headers: dict[str, str], db: Session
) -> None:
    application, secret, _ = provision_in_app(client, platform_headers)
    send = client.post(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {secret}", "Idempotency-Key": "in-app-1"},
        json={
            "event_key": "payment.pending",
            "channel": "in_app",
            "recipient": {"type": "user", "id": "usr_123"},
            "data": {"invoice_id": "INV-1024", "amount": "2500"},
            "priority": 8,
            "metadata": {"deduplication_key": "payment-pending-INV-1024"},
            "expires_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        },
    )
    assert send.status_code == 202, send.text
    process_notification(db, send.json()["id"], get_settings())
    in_app = db.scalar(select(InAppNotification))
    assert in_app is not None
    assert in_app.title == "Payment pending"
    assert in_app.action_payload["url"] == "/invoices/INV-1024"
    recipient = db.scalar(select(InAppRecipient))
    assert recipient is not None
    assert recipient.recipient_id == "usr_123"

    headers = user_headers(application)
    unread = client.get("/api/v1/in-app/unread-count", headers=headers)
    assert unread.status_code == 200
    assert unread.json()["unread"] == 1
    listing = client.get("/api/v1/in-app/notifications", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["items"][0]["read"] is False
    ack = client.post(
        f"/api/v1/in-app/notifications/{in_app.id}/ack",
        headers=headers,
        json={"status": "displayed", "device_id": "web-test", "session_id": "ses_test"},
    )
    assert ack.status_code == 200
    read = client.post(f"/api/v1/in-app/notifications/{in_app.id}/read", headers=headers)
    assert read.status_code == 200
    assert read.json()["read"] is True
    dismiss = client.post(f"/api/v1/in-app/notifications/{in_app.id}/dismiss", headers=headers)
    assert dismiss.status_code == 200
    assert dismiss.json()["dismissed_at"] is not None
    assert client.get("/api/v1/in-app/unread-count", headers=headers).json()["unread"] == 0

    pref = client.patch(
        "/api/v1/in-app/preferences",
        headers=headers,
        json={"event_key": "payment.pending", "toast_enabled": False, "minimum_priority": 7},
    )
    assert pref.status_code == 200
    assert pref.json()["toast_enabled"] is False


def test_in_app_deduplication_conflict_and_cross_tenant_denial(
    client: TestClient, platform_headers: dict[str, str], db: Session
) -> None:
    application, secret, _ = provision_in_app(client, platform_headers, "dedupe-a")
    other_application, _, _ = provision_in_app(client, platform_headers, "dedupe-b")
    payload = {
        "event_key": "payment.pending",
        "channel": "in_app",
        "recipient": {"type": "user", "id": "usr_123"},
        "data": {"invoice_id": "INV-1024", "amount": "2500"},
        "metadata": {"deduplication_key": "payment-pending-INV-1024"},
    }
    first = client.post(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {secret}", "Idempotency-Key": "dedupe-1"},
        json=payload,
    )
    assert first.status_code == 202
    process_notification(db, first.json()["id"], get_settings())
    second = client.post(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {secret}", "Idempotency-Key": "dedupe-2"},
        json={**payload, "data": {"invoice_id": "INV-1024", "amount": "9999"}},
    )
    assert second.status_code == 202
    process_notification(db, second.json()["id"], get_settings())
    failed = db.get(Notification, second.json()["id"])
    assert failed is not None
    assert failed.status == "failed"
    assert failed.failure_code == "IN_APP_DELIVERY_ERROR"

    denied = client.get("/api/v1/in-app/notifications", headers=user_headers(other_application))
    assert denied.status_code == 200
    assert denied.json()["items"] == []

