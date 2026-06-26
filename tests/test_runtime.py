from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from ett_gns_app.models import OutboxEvent
from tests.test_control_plane import create_tenant_and_app


def provision_runtime(
    client: TestClient, platform_headers: dict[str, str], suffix: str = "runtime"
) -> tuple[dict, str]:
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
            "event_key": "account.welcome",
            "allowed_channels": ["email"],
            "schema": {
                "type": "object",
                "required": ["name"],
                "properties": {"name": {"type": "string"}},
                "additionalProperties": False,
            },
        },
    )
    assert event.status_code == 201
    template = client.post(
        f"/api/v1/apps/{application['id']}/events/account.welcome/templates",
        headers=admin,
        json={
            "channel": "email",
            "locale": "en-IN",
            "content": {
                "subject": "Welcome {{ name }}",
                "html": "<p>Welcome {{ name }}</p>",
                "text": "Welcome {{ name }}",
            },
            "sample_data": {"name": "Ravi"},
        },
    )
    assert template.status_code == 201, template.text
    validated = client.post(
        f"/api/v1/template-versions/{template.json()['id']}/validate", headers=admin
    )
    assert validated.status_code == 200
    published = client.post(
        f"/api/v1/template-versions/{template.json()['id']}/publish", headers=admin
    )
    assert published.status_code == 200
    provider = client.post(
        f"/api/v1/apps/{application['id']}/providers",
        headers=admin,
        json={
            "channel": "email",
            "provider_type": "fake",
            "name": "Runtime fake",
            "public_config": {"from_email": "verified@example.test"},
            "secret": {"callback_secret": "callback-test-secret"},
        },
    )
    assert provider.status_code == 201, provider.text
    tested = client.post(f"/api/v1/providers/{provider.json()['id']}/test", headers=admin)
    assert tested.status_code == 200
    activated = client.post(f"/api/v1/providers/{provider.json()['id']}/activate", headers=admin)
    assert activated.status_code == 200
    credential = client.post(
        f"/api/v1/apps/{application['id']}/credentials",
        headers=admin,
        json={
            "name": "runtime",
            "permissions": [
                "notifications:send",
                "notifications:read",
                "notifications:cancel",
            ],
        },
    )
    assert credential.status_code == 201
    return application, credential.json()["secret"]


def test_notification_is_durable_idempotent_and_cancellable(
    client: TestClient, platform_headers: dict[str, str]
) -> None:
    application, secret = provision_runtime(client, platform_headers)
    headers = {"Authorization": f"Bearer {secret}", "Idempotency-Key": "welcome-1"}
    payload = {
        "app_id": application["id"],
        "event_key": "account.welcome",
        "channel": "email",
        "recipient": {"email": "person@example.com"},
        "data": {"name": "Ravi"},
        "metadata": {"correlation_id": "corr_1"},
    }
    first = client.post("/api/v1/notifications", headers=headers, json=payload)
    assert first.status_code == 202, first.text
    duplicate = client.post("/api/v1/notifications", headers=headers, json=payload)
    assert duplicate.status_code == 202
    assert duplicate.json()["id"] == first.json()["id"]
    conflict_payload = {**payload, "data": {"name": "Different"}}
    conflict = client.post("/api/v1/notifications", headers=headers, json=conflict_payload)
    assert conflict.status_code == 409
    status_response = client.get(
        f"/api/v1/notifications/{first.json()['id']}",
        headers={"Authorization": f"Bearer {secret}"},
    )
    assert status_response.status_code == 200
    cancelled = client.post(
        f"/api/v1/notifications/{first.json()['id']}/cancel",
        headers={"Authorization": f"Bearer {secret}"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"


def test_runtime_rejects_cross_application_and_bad_schema(
    client: TestClient, platform_headers: dict[str, str]
) -> None:
    first_app, first_secret = provision_runtime(client, platform_headers, "runtime-a")
    second_app, _ = provision_runtime(client, platform_headers, "runtime-b")
    cross_app = client.post(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {first_secret}", "Idempotency-Key": "cross"},
        json={
            "app_id": second_app["id"],
            "event_key": "account.welcome",
            "channel": "email",
            "recipient": {"email": "person@example.com"},
            "data": {"name": "Ravi"},
        },
    )
    assert cross_app.status_code == 403
    assert cross_app.json()["detail"]["code"] == "application_scope_mismatch"
    invalid_data = client.post(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {first_secret}", "Idempotency-Key": "invalid"},
        json={
            "app_id": first_app["id"],
            "event_key": "account.welcome",
            "channel": "email",
            "recipient": {"email": "person@example.com"},
            "data": {},
        },
    )
    assert invalid_data.status_code == 422


def test_runtime_derives_application_from_credential_when_app_id_is_omitted(
    client: TestClient, platform_headers: dict[str, str]
) -> None:
    application, secret = provision_runtime(client, platform_headers, "derived-app")
    response = client.post(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {secret}", "Idempotency-Key": "derived-app"},
        json={
            "event_key": "account.welcome",
            "channel": "email",
            "recipient": {"email": "person@example.com"},
            "data": {"name": "Ravi"},
        },
    )
    assert response.status_code == 202, response.text
    assert response.json()["application_id"] == application["id"]


def test_openapi_exposes_application_bearer_security(
    client: TestClient,
) -> None:
    schema = client.get("/openapi.json").json()
    assert schema["components"]["securitySchemes"]["ApplicationBearer"]["scheme"] == "bearer"
    assert schema["paths"]["/api/v1/notifications"]["post"]["security"] == [
        {"ApplicationBearer": []}
    ]


def test_quota_is_enforced_without_charging_idempotent_duplicate(
    client: TestClient, platform_headers: dict[str, str]
) -> None:
    application, secret = provision_runtime(client, platform_headers, "quota")
    tenant_headers = {
        "X-Admin-User": "tenant-admin",
        "X-Admin-Roles": "tenant_admin",
        "X-Tenant-ID": application["tenant_id"],
    }
    updated = client.patch(
        f"/api/v1/apps/{application['id']}",
        headers=tenant_headers,
        json={"quota_per_minute": 1, "quota_per_day": 10},
    )
    assert updated.status_code == 200
    payload = {
        "app_id": application["id"],
        "event_key": "account.welcome",
        "channel": "email",
        "recipient": {"email": "person@example.com"},
        "data": {"name": "Ravi"},
    }
    first_headers = {"Authorization": f"Bearer {secret}", "Idempotency-Key": "quota-1"}
    first = client.post("/api/v1/notifications", headers=first_headers, json=payload)
    assert first.status_code == 202
    duplicate = client.post("/api/v1/notifications", headers=first_headers, json=payload)
    assert duplicate.status_code == 202
    second = client.post(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {secret}", "Idempotency-Key": "quota-2"},
        json=payload,
    )
    assert second.status_code == 429


def test_scheduled_notification_propagates_outbox_eta(
    client: TestClient, platform_headers: dict[str, str], db: Session
) -> None:
    application, secret = provision_runtime(client, platform_headers, "scheduled")
    scheduled_at = datetime.now(UTC) + timedelta(hours=1)
    response = client.post(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {secret}", "Idempotency-Key": "scheduled-1"},
        json={
            "app_id": application["id"],
            "event_key": "account.welcome",
            "channel": "email",
            "recipient": {"email": "person@example.com"},
            "data": {"name": "Ravi"},
            "scheduled_at": scheduled_at.isoformat(),
        },
    )
    assert response.status_code == 202
    row = db.scalar(
        select(OutboxEvent).where(
            OutboxEvent.aggregate_id == response.json()["id"],
            OutboxEvent.event_type == "notification.scheduled",
        )
    )
    assert row is not None
    assert row.payload["available_at"] == scheduled_at.isoformat()
