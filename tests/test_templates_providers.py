from fastapi.testclient import TestClient

from tests.test_control_plane import create_tenant_and_app


def provision_event(
    client: TestClient, platform_headers: dict[str, str]
) -> tuple[dict, dict, dict[str, str]]:
    tenant, application = create_tenant_and_app(client, platform_headers, "templates")
    headers = {
        "X-Admin-User": "publisher",
        "X-Admin-Roles": "tenant_admin",
        "X-Tenant-ID": tenant["id"],
    }
    event_response = client.post(
        f"/api/v1/apps/{application['id']}/events",
        headers=headers,
        json={
            "event_key": "invoice.ready",
            "allowed_channels": ["email", "webhook"],
            "schema": {
                "type": "object",
                "required": ["customer_name", "invoice_url"],
                "properties": {
                    "customer_name": {"type": "string"},
                    "invoice_url": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
    )
    assert event_response.status_code == 201
    return tenant, application, headers


def test_template_validation_preview_publish_version_and_rollback(
    client: TestClient, platform_headers: dict[str, str]
) -> None:
    _, application, headers = provision_event(client, platform_headers)
    created = client.post(
        f"/api/v1/apps/{application['id']}/events/invoice.ready/templates",
        headers=headers,
        json={
            "channel": "email",
            "locale": "en-IN",
            "variant": "default",
            "content": {
                "subject": "Invoice for {{ customer_name }}",
                "html": "<p>Hello <strong>{{ customer_name }}</strong></p>",
                "text": "Hello {{ customer_name }}: {{ invoice_url }}",
            },
            "sample_data": {
                "customer_name": "Ravi",
                "invoice_url": "https://example.test/invoice",
            },
        },
    )
    assert created.status_code == 201, created.text
    version = created.json()
    validated = client.post(f"/api/v1/template-versions/{version['id']}/validate", headers=headers)
    assert validated.status_code == 200
    assert validated.json()["state"] == "validated"
    preview = client.post(
        f"/api/v1/template-versions/{version['id']}/preview",
        headers=headers,
        json={},
    )
    assert preview.status_code == 200
    assert "Ravi" in preview.json()["rendered"]["html"]
    published = client.post(f"/api/v1/template-versions/{version['id']}/publish", headers=headers)
    assert published.status_code == 200
    assert published.json()["state"] == "published"
    immutable = client.patch(
        f"/api/v1/template-versions/{version['id']}",
        headers=headers,
        json={"content": {"subject": "changed"}},
    )
    assert immutable.status_code == 409
    next_version = client.post(
        f"/api/v1/templates/{version['template_id']}/versions", headers=headers
    )
    assert next_version.status_code == 201
    assert next_version.json()["version"] == 2
    rollback = client.post(
        f"/api/v1/templates/{version['template_id']}/rollback/1", headers=headers
    )
    assert rollback.status_code == 200
    assert rollback.json()["version"] == 1


def test_template_test_send_uses_configured_adapter(
    client: TestClient, platform_headers: dict[str, str]
) -> None:
    _, application, headers = provision_event(client, platform_headers)
    provider = client.post(
        f"/api/v1/apps/{application['id']}/providers",
        headers=headers,
        json={
            "channel": "email",
            "provider_type": "fake",
            "name": "Test-send fake",
            "public_config": {"from_email": "verified@example.test"},
        },
    )
    client.post(f"/api/v1/providers/{provider.json()['id']}/test", headers=headers)
    client.post(f"/api/v1/providers/{provider.json()['id']}/activate", headers=headers)
    template = client.post(
        f"/api/v1/apps/{application['id']}/events/invoice.ready/templates",
        headers=headers,
        json={
            "channel": "email",
            "content": {
                "subject": "Invoice {{ customer_name }}",
                "html": "<p>{{ customer_name }}</p>",
                "text": "{{ invoice_url }}",
            },
            "sample_data": {
                "customer_name": "Ravi",
                "invoice_url": "https://example.test/invoice",
            },
        },
    )
    response = client.post(
        f"/api/v1/template-versions/{template.json()['id']}/test-send",
        headers=headers,
        json={"recipient": {"email": "test@example.com"}},
    )
    assert response.status_code == 200, response.text
    assert response.json()["provider_message_id"].startswith("fake_")


def test_template_blocks_unknown_variables_and_unsafe_html(
    client: TestClient, platform_headers: dict[str, str]
) -> None:
    _, application, headers = provision_event(client, platform_headers)
    created = client.post(
        f"/api/v1/apps/{application['id']}/events/invoice.ready/templates",
        headers=headers,
        json={
            "channel": "email",
            "content": {
                "subject": "{{ unknown }}",
                "html": "<script>alert(1)</script><p>{{ customer_name }}</p>",
                "text": "{{ customer_name }}",
            },
            "sample_data": {
                "customer_name": "Ravi",
                "invoice_url": "https://example.test/invoice",
            },
        },
    )
    assert created.status_code == 201
    validated = client.post(
        f"/api/v1/template-versions/{created.json()['id']}/validate", headers=headers
    )
    assert validated.status_code == 200
    errors = validated.json()["validation_errors"]
    assert any("undeclared variables" in error for error in errors)
    assert any("disallowed" in error for error in errors)


def test_provider_secrets_are_masked_verified_and_activation_gated(
    client: TestClient, platform_headers: dict[str, str]
) -> None:
    tenant, application, headers = provision_event(client, platform_headers)
    invalid = client.post(
        f"/api/v1/apps/{application['id']}/providers",
        headers=headers,
        json={
            "channel": "email",
            "provider_type": "smtp",
            "name": "Incomplete SMTP",
            "public_config": {"host": "smtp.example.test"},
            "secret": {},
        },
    )
    assert invalid.status_code == 422
    created = client.post(
        f"/api/v1/apps/{application['id']}/providers",
        headers=headers,
        json={
            "channel": "email",
            "provider_type": "fake",
            "name": "Deterministic fake",
            "public_config": {},
            "secret": {"token": "never-return-this"},
        },
    )
    assert created.status_code == 201, created.text
    provider = created.json()
    assert provider["secret_configured"] is True
    assert "secret" not in provider
    blocked = client.post(f"/api/v1/providers/{provider['id']}/activate", headers=headers)
    assert blocked.status_code == 409
    tested = client.post(f"/api/v1/providers/{provider['id']}/test", headers=headers)
    assert tested.status_code == 200
    assert tested.json()["valid"] is True
    activated = client.post(f"/api/v1/providers/{provider['id']}/activate", headers=headers)
    assert activated.status_code == 200
    assert activated.json()["active"] is True
    listing = client.get(f"/api/v1/tenants/{tenant['id']}/providers", headers=headers)
    assert listing.status_code == 200
    assert "never-return-this" not in listing.text
