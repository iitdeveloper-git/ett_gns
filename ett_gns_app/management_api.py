from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ett_gns_app.api import audit, ensure_tenant, fail, get_application
from ett_gns_app.channels import AdapterError, SMTPAdapter, adapter_for
from ett_gns_app.database import get_db
from ett_gns_app.models import (
    Application,
    Event,
    EventSchemaVersion,
    Lifecycle,
    Notification,
    ProviderConfig,
    Template,
    TemplateState,
    TemplateVersion,
)
from ett_gns_app.resolution import ResolutionError, resolve_email_sender, resolve_provider
from ett_gns_app.schemas import (
    Page,
    ProviderCreate,
    ProviderRead,
    ProviderSecretReplace,
    ProviderTestResult,
    ProviderUpdate,
    RenderedPreview,
    TemplateCreate,
    TemplatePreview,
    TemplateRead,
    TemplateTestSend,
    TemplateUpdate,
    TemplateVersionRead,
)
from ett_gns_app.secrets import SecretStore
from ett_gns_app.security import Principal, require
from ett_gns_app.settings import Settings, get_settings
from ett_gns_app.template_service import render_content, validate_template_content

router = APIRouter(prefix="/api/v1")

SUPPORTED_PROVIDER_TYPES = {
    "email": {"smtp", "fake"},
    "sms": {"twilio", "fake"},
    "webhook": {"http", "fake"},
    "push": {"fcm", "fake"},
    "telegram": {"telegram_bot", "fake"},
    "whatsapp": {"meta_cloud", "fake"},
}


def get_event_schema(db: Session, event: Event) -> dict[str, Any]:
    version = db.scalar(
        select(EventSchemaVersion).where(
            EventSchemaVersion.event_id == event.id,
            EventSchemaVersion.version == event.current_schema_version,
        )
    )
    if not version:
        fail(500, "schema_missing", "Current event schema is unavailable")
    return version.schema


def get_template_version(
    db: Session, version_id: str, principal: Principal
) -> tuple[TemplateVersion, Template]:
    version = db.get(TemplateVersion, version_id)
    if not version:
        fail(404, "template_version_not_found", "Template version not found")
    template = db.get(Template, version.template_id)
    if not template:
        fail(404, "template_not_found", "Template not found")
    ensure_tenant(principal, template.tenant_id)
    return version, template


def validate_provider(
    channel: str, provider_type: str, public_config: dict[str, Any], secret: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    if provider_type not in SUPPORTED_PROVIDER_TYPES.get(channel, set()):
        return [f"Provider type {provider_type!r} is unsupported for channel {channel!r}"]
    if provider_type == "fake":
        return []
    required_public: dict[str, set[str]] = {
        "smtp": {"host", "port", "security", "from_email"},
        "twilio": {"account_sid", "from_number"},
        "http": {"url"},
        "fcm": {"project_id"},
        "telegram_bot": set(),
        "meta_cloud": {"phone_number_id", "api_version"},
    }
    required_secret: dict[str, set[str]] = {
        "smtp": {"password"},
        "twilio": {"auth_token"},
        "http": set(),
        "fcm": {"service_account"},
        "telegram_bot": {"bot_token"},
        "meta_cloud": {"access_token", "app_secret"},
    }
    missing_public = required_public[provider_type] - public_config.keys()
    missing_secret = required_secret[provider_type] - secret.keys()
    if missing_public:
        errors.append(f"Missing public config: {sorted(missing_public)}")
    if missing_secret:
        errors.append(f"Missing secret config: {sorted(missing_secret)}")
    if provider_type == "smtp":
        security = public_config.get("security")
        if security not in {"ssl", "starttls", "plain"}:
            errors.append("SMTP security must be ssl, starttls, or plain")
        port = public_config.get("port")
        if not isinstance(port, int) or not 1 <= port <= 65535:
            errors.append("SMTP port must be between 1 and 65535")
    if provider_type == "http":
        url = str(public_config.get("url", ""))
        if not url.startswith("https://"):
            errors.append("Webhook provider URL must use HTTPS")
        if not secret.get("signing_secret") and not secret.get("signing_secrets"):
            errors.append("Webhook signing secret is required")
    return errors


@router.post(
    "/apps/{app_id}/events/{event_key}/templates",
    response_model=TemplateVersionRead,
    status_code=201,
)
def create_template(
    app_id: str,
    event_key: str,
    body: TemplateCreate,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("templates:write")),
) -> TemplateVersion:
    app = get_application(db, app_id, principal)
    event = db.scalar(
        select(Event).where(Event.application_id == app.id, Event.event_key == event_key)
    )
    if not event:
        fail(404, "event_not_found", "Event not found")
    template = Template(
        tenant_id=app.tenant_id,
        application_id=app.id,
        event_id=event.id,
        channel=body.channel,
        locale=body.locale,
        variant=body.variant,
    )
    db.add(template)
    try:
        db.flush()
        version = TemplateVersion(
            tenant_id=app.tenant_id,
            template_id=template.id,
            version=1,
            content=body.content,
            sample_data=body.sample_data,
        )
        db.add(version)
        db.flush()
        audit(
            db,
            principal,
            "template.created",
            "template",
            template.id,
            request.state.request_id,
            {
                "event_key": event_key,
                "channel": body.channel,
                "locale": body.locale,
                "variant": body.variant,
            },
            app.tenant_id,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        fail(409, "template_identity_exists", "Template identity already exists")
    return version


@router.get("/apps/{app_id}/templates", response_model=Page)
def list_templates(
    app_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("apps:read")),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page:
    app = get_application(db, app_id, principal)
    query = select(Template).where(Template.application_id == app.id)
    total = db.scalar(
        select(func.count()).select_from(Template).where(Template.application_id == app.id)
    )
    items = list(db.scalars(query.order_by(Template.created_at.desc()).limit(limit).offset(offset)))
    return Page(
        items=[TemplateRead.model_validate(item).model_dump(mode="json") for item in items],
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.get("/templates/{template_id}/versions", response_model=Page)
def list_template_versions(
    template_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("apps:read")),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page:
    template = db.get(Template, template_id)
    if not template:
        fail(404, "template_not_found", "Template not found")
    ensure_tenant(principal, template.tenant_id)
    query = select(TemplateVersion).where(TemplateVersion.template_id == template.id)
    total = db.scalar(
        select(func.count())
        .select_from(TemplateVersion)
        .where(TemplateVersion.template_id == template.id)
    )
    items = list(
        db.scalars(query.order_by(TemplateVersion.version.desc()).limit(limit).offset(offset))
    )
    return Page(
        items=[TemplateVersionRead.model_validate(item).model_dump(mode="json") for item in items],
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.patch("/template-versions/{version_id}", response_model=TemplateVersionRead)
def edit_template_version(
    version_id: str,
    body: TemplateUpdate,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("templates:write")),
) -> TemplateVersion:
    version, template = get_template_version(db, version_id, principal)
    if version.state not in {TemplateState.DRAFT, TemplateState.VALIDATED}:
        fail(409, "published_template_immutable", "Published template versions cannot be edited")
    changes = body.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(version, key, value)
    version.state = TemplateState.DRAFT
    version.validation_errors = []
    audit(
        db,
        principal,
        "template_version.updated",
        "template_version",
        version.id,
        request.state.request_id,
        {"fields": sorted(changes)},
        template.tenant_id,
    )
    db.commit()
    return version


@router.post("/template-versions/{version_id}/validate", response_model=TemplateVersionRead)
def validate_template_version(
    version_id: str,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("templates:write")),
) -> TemplateVersion:
    version, template = get_template_version(db, version_id, principal)
    if version.state not in {TemplateState.DRAFT, TemplateState.VALIDATED}:
        fail(409, "invalid_template_state", "Only draft versions can be validated")
    event = db.get(Event, template.event_id)
    if not event:
        fail(500, "event_missing", "Template event is unavailable")
    errors = validate_template_content(
        template.channel,
        version.content,
        get_event_schema(db, event),
        version.sample_data,
    )
    version.validation_errors = errors
    version.state = TemplateState.VALIDATED if not errors else TemplateState.DRAFT
    audit(
        db,
        principal,
        "template_version.validated",
        "template_version",
        version.id,
        request.state.request_id,
        {"valid": not errors, "error_count": len(errors)},
        template.tenant_id,
    )
    db.commit()
    return version


@router.post("/template-versions/{version_id}/preview", response_model=RenderedPreview)
def preview_template_version(
    version_id: str,
    body: TemplatePreview,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("templates:write")),
) -> RenderedPreview:
    version, template = get_template_version(db, version_id, principal)
    data = body.data if body.data is not None else version.sample_data
    event = db.get(Event, template.event_id)
    if not event:
        fail(500, "event_missing", "Template event is unavailable")
    errors = validate_template_content(
        template.channel, version.content, get_event_schema(db, event), data
    )
    if errors:
        fail(422, "template_invalid", "; ".join(errors))
    return RenderedPreview(
        rendered=render_content(version.content, data),
        locale=template.locale,
        variant=template.variant,
        version=version.version,
    )


@router.post("/template-versions/{version_id}/test-send")
def test_send_template_version(
    version_id: str,
    body: TemplateTestSend,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("templates:write")),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    version, template = get_template_version(db, version_id, principal)
    event = db.get(Event, template.event_id)
    app = db.get(Application, template.application_id)
    if not event or not app:
        fail(500, "template_context_missing", "Template application or event is unavailable")
    data = body.data if body.data is not None else version.sample_data
    errors = validate_template_content(
        template.channel, version.content, get_event_schema(db, event), data
    )
    if errors:
        fail(422, "template_invalid", "; ".join(errors))
    try:
        provider = resolve_provider(db, app, template.channel)
        secret = SecretStore(settings).decrypt(provider.secret_ciphertext)
        sender = resolve_email_sender(app, provider) if template.channel == "email" else {}
        result = adapter_for(template.channel, provider.provider_type).send(
            provider.public_config,
            secret,
            sender,
            body.recipient,
            render_content(version.content, data),
            {"test_send": True, "requested_by": principal.subject},
        )
    except (ResolutionError, AdapterError) as exc:
        code = getattr(exc, "code", "test_send_failed")
        fail(409, code, str(exc))
    audit(
        db,
        principal,
        "template.test_sent",
        "template_version",
        version.id,
        request.state.request_id,
        {"channel": template.channel, "provider_id": provider.id},
        template.tenant_id,
    )
    db.commit()
    return {
        "accepted": result.accepted,
        "provider_message_id": result.provider_message_id,
        "status": result.status,
    }


@router.post("/template-versions/{version_id}/publish", response_model=TemplateVersionRead)
def publish_template_version(
    version_id: str,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("templates:publish")),
) -> TemplateVersion:
    version, template = get_template_version(db, version_id, principal)
    if version.state != TemplateState.VALIDATED or version.validation_errors:
        fail(409, "template_not_validated", "Template must pass validation before publishing")
    current = None
    if template.published_version is not None:
        current = db.scalar(
            select(TemplateVersion).where(
                TemplateVersion.template_id == template.id,
                TemplateVersion.version == template.published_version,
            )
        )
    if current:
        current.state = TemplateState.DEPRECATED
    version.state = TemplateState.PUBLISHED
    version.published_at = datetime.now(UTC)
    version.published_by = principal.subject
    template.published_version = version.version
    audit(
        db,
        principal,
        "template_version.published",
        "template_version",
        version.id,
        request.state.request_id,
        {"version": version.version},
        template.tenant_id,
    )
    db.commit()
    return version


@router.post(
    "/templates/{template_id}/versions", response_model=TemplateVersionRead, status_code=201
)
def create_next_template_version(
    template_id: str,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("templates:write")),
) -> TemplateVersion:
    template = db.get(Template, template_id)
    if not template:
        fail(404, "template_not_found", "Template not found")
    ensure_tenant(principal, template.tenant_id)
    latest = db.scalar(
        select(TemplateVersion)
        .where(TemplateVersion.template_id == template.id)
        .order_by(TemplateVersion.version.desc())
    )
    if not latest:
        fail(500, "template_version_missing", "Template has no version")
    version = TemplateVersion(
        tenant_id=template.tenant_id,
        template_id=template.id,
        version=latest.version + 1,
        content=latest.content,
        sample_data=latest.sample_data,
    )
    db.add(version)
    db.flush()
    audit(
        db,
        principal,
        "template_version.created",
        "template_version",
        version.id,
        request.state.request_id,
        {"version": version.version, "based_on": latest.version},
        template.tenant_id,
    )
    db.commit()
    return version


@router.post("/templates/{template_id}/rollback/{version}", response_model=TemplateVersionRead)
def rollback_template(
    template_id: str,
    version: int,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("templates:publish")),
) -> TemplateVersion:
    template = db.get(Template, template_id)
    if not template:
        fail(404, "template_not_found", "Template not found")
    ensure_tenant(principal, template.tenant_id)
    target = db.scalar(
        select(TemplateVersion).where(
            TemplateVersion.template_id == template.id,
            TemplateVersion.version == version,
        )
    )
    if not target or target.state not in {TemplateState.PUBLISHED, TemplateState.DEPRECATED}:
        fail(409, "rollback_target_invalid", "Rollback requires a previously published version")
    current = db.scalar(
        select(TemplateVersion).where(
            TemplateVersion.template_id == template.id,
            TemplateVersion.version == template.published_version,
        )
    )
    if current:
        current.state = TemplateState.DEPRECATED
    target.state = TemplateState.PUBLISHED
    target.published_at = datetime.now(UTC)
    target.published_by = principal.subject
    template.published_version = target.version
    audit(
        db,
        principal,
        "template.rolled_back",
        "template",
        template.id,
        request.state.request_id,
        {"version": version},
        template.tenant_id,
    )
    db.commit()
    return target


@router.post("/templates/{template_id}/{action}", response_model=TemplateRead)
def transition_template(
    template_id: str,
    action: str,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("templates:write")),
) -> Template:
    if action not in {"deprecate", "archive"}:
        fail(404, "not_found", "Action not found")
    template = db.get(Template, template_id)
    if not template:
        fail(404, "template_not_found", "Template not found")
    ensure_tenant(principal, template.tenant_id)
    template.status = Lifecycle.DISABLED if action == "deprecate" else Lifecycle.ARCHIVED
    audit(
        db,
        principal,
        f"template.{action}d",
        "template",
        template.id,
        request.state.request_id,
        tenant_id=template.tenant_id,
    )
    db.commit()
    return template


def create_provider_record(
    db: Session,
    principal: Principal,
    request: Request,
    body: ProviderCreate,
    tenant_id: str,
    application_id: str | None,
    settings: Settings,
) -> ProviderConfig:
    ensure_tenant(principal, tenant_id)
    secret = body.secret or {}
    errors = validate_provider(body.channel, body.provider_type, body.public_config, secret)
    if errors:
        fail(422, "provider_config_invalid", "; ".join(errors))
    if body.is_default and application_id is not None:
        fail(422, "invalid_default_scope", "Only tenant/global providers can be defaults")
    if body.fallback_policy == "explicit_failover" and not body.fallback_provider_id:
        fail(
            422,
            "fallback_provider_required",
            "Explicit failover requires a fallback provider ID",
        )
    if body.fallback_provider_id:
        fallback = db.get(ProviderConfig, body.fallback_provider_id)
        if (
            not fallback
            or fallback.tenant_id != tenant_id
            or fallback.application_id != application_id
            or fallback.channel != body.channel
        ):
            fail(
                422,
                "fallback_provider_invalid",
                "Fallback provider must have the same scope and channel",
            )
    if body.is_default:
        existing = db.scalar(
            select(ProviderConfig).where(
                ProviderConfig.tenant_id == tenant_id,
                ProviderConfig.application_id.is_(None),
                ProviderConfig.channel == body.channel,
                ProviderConfig.is_default.is_(True),
            )
        )
        if existing:
            fail(409, "default_provider_exists", "Default provider already exists for channel")
    provider = ProviderConfig(
        tenant_id=tenant_id,
        application_id=application_id,
        channel=body.channel,
        provider_type=body.provider_type,
        name=body.name,
        public_config=body.public_config,
        secret_ciphertext=SecretStore(settings).encrypt(secret) if secret else None,
        secret_key_id="local-fernet-v1" if secret else None,
        is_default=body.is_default,
        fallback_policy=body.fallback_policy,
        fallback_provider_id=body.fallback_provider_id,
        health_status="configured",
    )
    db.add(provider)
    db.flush()
    audit(
        db,
        principal,
        "provider.created",
        "provider",
        provider.id,
        request.state.request_id,
        {
            "channel": body.channel,
            "provider_type": body.provider_type,
            "application_id": application_id,
            "secret_configured": bool(secret),
        },
        tenant_id,
    )
    db.commit()
    return provider


@router.post("/tenants/{tenant_id}/providers", response_model=ProviderRead, status_code=201)
def create_tenant_provider(
    tenant_id: str,
    body: ProviderCreate,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("providers:manage")),
    settings: Settings = Depends(get_settings),
) -> ProviderRead:
    provider = create_provider_record(db, principal, request, body, tenant_id, None, settings)
    result = ProviderRead.model_validate(provider)
    result.secret_configured = provider.secret_ciphertext is not None
    return result


@router.post("/apps/{app_id}/providers", response_model=ProviderRead, status_code=201)
def create_app_provider(
    app_id: str,
    body: ProviderCreate,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("providers:manage")),
    settings: Settings = Depends(get_settings),
) -> ProviderRead:
    app = get_application(db, app_id, principal)
    provider = create_provider_record(db, principal, request, body, app.tenant_id, app.id, settings)
    result = ProviderRead.model_validate(provider)
    result.secret_configured = provider.secret_ciphertext is not None
    return result


@router.get("/tenants/{tenant_id}/providers", response_model=Page)
def list_providers(
    tenant_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("apps:read")),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page:
    ensure_tenant(principal, tenant_id)
    query = select(ProviderConfig).where(ProviderConfig.tenant_id == tenant_id)
    total = db.scalar(
        select(func.count())
        .select_from(ProviderConfig)
        .where(ProviderConfig.tenant_id == tenant_id)
    )
    items = list(
        db.scalars(query.order_by(ProviderConfig.created_at.desc()).limit(limit).offset(offset))
    )
    output = []
    for item in items:
        read = ProviderRead.model_validate(item)
        read.secret_configured = item.secret_ciphertext is not None
        output.append(read.model_dump(mode="json"))
    return Page(items=output, total=total or 0, limit=limit, offset=offset)


def get_provider(db: Session, provider_id: str, principal: Principal) -> ProviderConfig:
    provider = db.get(ProviderConfig, provider_id)
    if not provider:
        fail(404, "provider_not_found", "Provider not found")
    ensure_tenant(principal, provider.tenant_id)
    return provider


@router.patch("/providers/{provider_id}", response_model=ProviderRead)
def update_provider(
    provider_id: str,
    body: ProviderUpdate,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("providers:manage")),
) -> ProviderRead:
    provider = get_provider(db, provider_id, principal)
    changes = body.model_dump(exclude_unset=True)
    if changes.get("is_default") and provider.application_id is not None:
        fail(422, "invalid_default_scope", "App-specific providers cannot be defaults")
    fallback_id = changes.get("fallback_provider_id")
    if fallback_id:
        fallback = db.get(ProviderConfig, fallback_id)
        if (
            not fallback
            or fallback.id == provider.id
            or fallback.tenant_id != provider.tenant_id
            or fallback.application_id != provider.application_id
            or fallback.channel != provider.channel
        ):
            fail(
                422,
                "fallback_provider_invalid",
                "Fallback provider must be a different provider with the same scope and channel",
            )
    if changes.get(
        "fallback_policy", provider.fallback_policy
    ) == "explicit_failover" and not changes.get(
        "fallback_provider_id", provider.fallback_provider_id
    ):
        fail(
            422,
            "fallback_provider_required",
            "Explicit failover requires a fallback provider ID",
        )
    for key, value in changes.items():
        setattr(provider, key, value)
    provider.health_status = "configured"
    provider.verified_at = None
    audit(
        db,
        principal,
        "provider.updated",
        "provider",
        provider.id,
        request.state.request_id,
        {"fields": sorted(changes)},
        provider.tenant_id,
    )
    db.commit()
    read = ProviderRead.model_validate(provider)
    read.secret_configured = provider.secret_ciphertext is not None
    return read


@router.put("/providers/{provider_id}/secret", response_model=ProviderRead)
def replace_provider_secret(
    provider_id: str,
    body: ProviderSecretReplace,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("providers:manage")),
    settings: Settings = Depends(get_settings),
) -> ProviderRead:
    provider = get_provider(db, provider_id, principal)
    errors = validate_provider(
        provider.channel, provider.provider_type, provider.public_config, body.secret
    )
    if errors:
        fail(422, "provider_config_invalid", "; ".join(errors))
    provider.secret_ciphertext = SecretStore(settings).encrypt(body.secret)
    provider.secret_key_id = "local-fernet-v1"  # noqa: S105 - key identifier, not a secret
    provider.health_status = "configured"
    provider.verified_at = None
    audit(
        db,
        principal,
        "provider.secret_replaced",
        "provider",
        provider.id,
        request.state.request_id,
        tenant_id=provider.tenant_id,
    )
    db.commit()
    read = ProviderRead.model_validate(provider)
    read.secret_configured = True
    return read


@router.post("/providers/{provider_id}/test", response_model=ProviderTestResult)
def test_provider(
    provider_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("providers:manage")),
    settings: Settings = Depends(get_settings),
) -> ProviderTestResult:
    provider = get_provider(db, provider_id, principal)
    secret = SecretStore(settings).decrypt(provider.secret_ciphertext)
    errors = validate_provider(
        provider.channel, provider.provider_type, provider.public_config, secret
    )
    if not errors and provider.provider_type == "smtp":
        try:
            SMTPAdapter().test_connection(provider.public_config, secret)
        except AdapterError as exc:
            errors.append(f"{exc.code}: {exc}")
    provider.health_status = "healthy" if not errors else "invalid"
    provider.verified_at = datetime.now(UTC) if not errors else None
    provider.last_error_code = None if not errors else "CONFIG_INVALID"
    db.commit()
    return ProviderTestResult(valid=not errors, health_status=provider.health_status, errors=errors)


@router.post("/providers/{provider_id}/{action}", response_model=ProviderRead)
def transition_provider(
    provider_id: str,
    action: str,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("providers:manage")),
) -> ProviderRead:
    if action not in {"activate", "deactivate"}:
        fail(404, "not_found", "Action not found")
    provider = get_provider(db, provider_id, principal)
    if action == "activate" and provider.health_status != "healthy":
        fail(409, "provider_not_verified", "Provider must pass verification before activation")
    provider.active = action == "activate"
    audit(
        db,
        principal,
        f"provider.{action}d",
        "provider",
        provider.id,
        request.state.request_id,
        tenant_id=provider.tenant_id,
    )
    db.commit()
    read = ProviderRead.model_validate(provider)
    read.secret_configured = provider.secret_ciphertext is not None
    return read


@router.delete("/providers/{provider_id}", status_code=204)
def delete_provider(
    provider_id: str,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("providers:manage")),
) -> None:
    provider = get_provider(db, provider_id, principal)
    referenced = db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.provider_config_id == provider.id)
    )
    if referenced:
        fail(409, "provider_in_use", "Provider is referenced by notification snapshots")
    if provider.active:
        fail(409, "provider_active", "Deactivate provider before deletion")
    audit(
        db,
        principal,
        "provider.deleted",
        "provider",
        provider.id,
        request.state.request_id,
        tenant_id=provider.tenant_id,
    )
    db.delete(provider)
    db.commit()
