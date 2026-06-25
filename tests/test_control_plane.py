from fastapi.testclient import TestClient


def create_tenant_and_app(
    client: TestClient, headers: dict[str, str], suffix: str = "one"
) -> tuple[dict, dict]:
    tenant_response = client.post(
        "/api/v1/tenants",
        headers=headers,
        json={"name": f"Tenant {suffix}", "slug": f"tenant-{suffix}"},
    )
    assert tenant_response.status_code == 201, tenant_response.text
    tenant = tenant_response.json()
    app_response = client.post(
        f"/api/v1/tenants/{tenant['id']}/apps",
        headers=headers,
        json={
            "name": f"Application {suffix}",
            "slug": f"application-{suffix}",
            "default_locale": "en-IN",
            "timezone": "Asia/Kolkata",
        },
    )
    assert app_response.status_code == 201, app_response.text
    return tenant, app_response.json()


def test_tenant_application_lifecycle_and_isolation(
    client: TestClient, platform_headers: dict[str, str]
) -> None:
    tenant, application = create_tenant_and_app(client, platform_headers)
    tenant_admin = {
        "X-Admin-User": "tenant-admin",
        "X-Admin-Roles": "tenant_admin",
        "X-Tenant-ID": tenant["id"],
    }
    response = client.get(f"/api/v1/apps/{application['id']}", headers=tenant_admin)
    assert response.status_code == 200
    other_tenant, other_app = create_tenant_and_app(client, platform_headers, "other")
    assert other_tenant["id"] != tenant["id"]
    denied = client.get(f"/api/v1/apps/{other_app['id']}", headers=tenant_admin)
    assert denied.status_code == 404
    disabled = client.post(
        f"/api/v1/apps/{application['id']}/actions/disable", headers=tenant_admin
    )
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "disabled"
    archived = client.post(
        f"/api/v1/apps/{application['id']}/actions/archive", headers=tenant_admin
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"


def test_credentials_are_shown_once_hashed_rotated_and_revoked(
    client: TestClient, platform_headers: dict[str, str]
) -> None:
    tenant, application = create_tenant_and_app(client, platform_headers)
    headers = {
        "X-Admin-User": "tenant-admin",
        "X-Admin-Roles": "tenant_admin",
        "X-Tenant-ID": tenant["id"],
    }
    created = client.post(
        f"/api/v1/apps/{application['id']}/credentials",
        headers=headers,
        json={
            "name": "runtime",
            "permissions": [
                "notifications:send",
                "notifications:read",
                "notifications:cancel",
            ],
        },
    )
    assert created.status_code == 201, created.text
    credential = created.json()
    assert credential["secret"].startswith("gns_")
    listed = client.get(f"/api/v1/apps/{application['id']}/credentials", headers=headers)
    assert listed.status_code == 200
    assert "secret" not in listed.json()["items"][0]
    rotated = client.post(
        f"/api/v1/credentials/{credential['id']}/rotate",
        headers=headers,
        json={"overlap_seconds": 0},
    )
    assert rotated.status_code == 201
    assert rotated.json()["secret"] != credential["secret"]
    revoked = client.post(f"/api/v1/credentials/{rotated.json()['id']}/revoke", headers=headers)
    assert revoked.status_code == 200
    assert revoked.json()["revoked_at"] is not None


def test_event_schema_versioning_and_compatibility(
    client: TestClient, platform_headers: dict[str, str]
) -> None:
    tenant, application = create_tenant_and_app(client, platform_headers)
    headers = {
        "X-Admin-User": "editor",
        "X-Admin-Roles": "tenant_admin",
        "X-Tenant-ID": tenant["id"],
    }
    created = client.post(
        f"/api/v1/apps/{application['id']}/events",
        headers=headers,
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
    assert created.status_code == 201, created.text
    event = created.json()
    incompatible = client.patch(
        f"/api/v1/events/{event['id']}",
        headers=headers,
        json={
            "schema": {
                "type": "object",
                "required": ["name", "company"],
                "properties": {
                    "name": {"type": "string"},
                    "company": {"type": "string"},
                },
            },
            "compatibility": "backward",
        },
    )
    assert incompatible.status_code == 409
    compatible = client.patch(
        f"/api/v1/events/{event['id']}",
        headers=headers,
        json={
            "schema": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {"type": "string"},
                    "company": {"type": "string"},
                },
            },
            "compatibility": "backward",
        },
    )
    assert compatible.status_code == 200
    assert compatible.json()["current_schema_version"] == 2
