import pytest
from sqlalchemy.orm import Session

from ett_gns_app.models import Application, ProviderConfig, Tenant
from ett_gns_app.resolution import ResolutionError, resolve_email_sender, resolve_provider


def test_app_provider_wins_and_unhealthy_app_provider_never_silently_falls_back(
    db: Session,
) -> None:
    tenant = Tenant(name="Tenant", slug="resolution-tenant")
    db.add(tenant)
    db.flush()
    app = Application(
        tenant_id=tenant.id,
        name="Application",
        slug="resolution-app",
        branding={"display_name": "App Brand"},
    )
    db.add(app)
    db.flush()
    default = ProviderConfig(
        tenant_id=tenant.id,
        channel="email",
        provider_type="smtp",
        name="Default",
        public_config={"from_email": "platform@example.test"},
        active=True,
        is_default=True,
        fallback_policy="default_if_absent",
        health_status="healthy",
    )
    app_provider = ProviderConfig(
        tenant_id=tenant.id,
        application_id=app.id,
        channel="email",
        provider_type="smtp",
        name="App",
        public_config={"from_email": "app@example.test"},
        active=True,
        health_status="healthy",
    )
    db.add_all([default, app_provider])
    db.commit()
    assert resolve_provider(db, app, "email").id == app_provider.id
    app_provider.health_status = "authentication_failed"
    db.commit()
    with pytest.raises(ResolutionError, match="app-specific provider"):
        resolve_provider(db, app, "email")


def test_default_sender_preserves_authenticated_from_and_verifies_reply_to(
    db: Session,
) -> None:
    tenant = Tenant(name="Tenant", slug="sender-tenant")
    db.add(tenant)
    db.flush()
    app = Application(
        tenant_id=tenant.id,
        name="App",
        slug="sender-app",
        branding={
            "display_name": "Customer Brand",
            "from_email": "forbidden@customer.test",
            "reply_to": "support@customer.test",
        },
    )
    provider = ProviderConfig(
        tenant_id=tenant.id,
        channel="email",
        provider_type="smtp",
        name="Default",
        public_config={
            "from_email": "authenticated@platform.test",
            "from_name": "Platform",
            "allow_app_display_name": True,
            "verified_reply_to": ["support@customer.test"],
        },
        active=True,
        is_default=True,
        fallback_policy="default_if_absent",
        health_status="healthy",
    )
    sender = resolve_email_sender(app, provider)
    assert sender["from_email"] == "authenticated@platform.test"
    assert sender["from_name"] == "Customer Brand"
    assert sender["reply_to"] == "support@customer.test"
    assert "forbidden@customer.test" not in sender.values()


def test_explicit_secondary_is_used_only_for_non_authentication_outage(
    db: Session,
) -> None:
    tenant = Tenant(name="Tenant", slug="failover-tenant")
    db.add(tenant)
    db.flush()
    app = Application(tenant_id=tenant.id, name="App", slug="failover-app")
    db.add(app)
    db.flush()
    secondary = ProviderConfig(
        tenant_id=tenant.id,
        application_id=app.id,
        channel="email",
        provider_type="smtp",
        name="Secondary",
        public_config={"from_email": "secondary@example.test"},
        active=True,
        health_status="healthy",
    )
    db.add(secondary)
    db.flush()
    primary = ProviderConfig(
        tenant_id=tenant.id,
        application_id=app.id,
        channel="email",
        provider_type="smtp",
        name="Primary",
        public_config={"from_email": "primary@example.test"},
        active=True,
        health_status="temporarily_unavailable",
        fallback_policy="explicit_failover",
        fallback_provider_id=secondary.id,
    )
    db.add(primary)
    db.commit()
    assert resolve_provider(db, app, "email").id == secondary.id
    primary.health_status = "authentication_failed"
    db.commit()
    with pytest.raises(ResolutionError):
        resolve_provider(db, app, "email")
