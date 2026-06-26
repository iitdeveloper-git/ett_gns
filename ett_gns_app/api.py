from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any, NoReturn

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ett_gns_app.database import get_db
from ett_gns_app.models import (
    Application,
    ApplicationCredential,
    AuditEvent,
    Event,
    EventSchemaVersion,
    Lifecycle,
    Notification,
    NotificationStatus,
    OutboxEvent,
    Tenant,
)
from ett_gns_app.quotas import QuotaExceeded, consume_quota
from ett_gns_app.resolution import ResolutionError, resolve_delivery
from ett_gns_app.schemas import (
    ApplicationCreate,
    ApplicationRead,
    ApplicationUpdate,
    CredentialCreate,
    CredentialRead,
    CredentialSecret,
    EventCreate,
    EventRead,
    EventUpdate,
    NotificationCreate,
    NotificationRead,
    Page,
    RotateCredential,
    SchemaVersionRead,
    TenantCreate,
    TenantRead,
    TenantUpdate,
)
from ett_gns_app.security import (
    Principal,
    generate_api_key,
    get_app_principal,
    require,
)
from ett_gns_app.settings import Settings, get_settings

router = APIRouter(prefix="/api/v1")

CHANNEL_RECIPIENT_KEYS = {
    "email": "email",
    "sms": "phone",
    "webhook": "url",
    "push": "token",
    "telegram": "chat_id",
    "whatsapp": "phone",
}
VALID_CREDENTIAL_PERMISSIONS = {
    "notifications:send",
    "notifications:read",
    "notifications:cancel",
}


def fail(code: int, error_code: str, message: str) -> NoReturn:
    raise HTTPException(status_code=code, detail={"code": error_code, "message": message})


def ensure_tenant(principal: Principal, tenant_id: str) -> None:
    if "*" not in principal.permissions and principal.tenant_id != tenant_id:
        fail(status.HTTP_404_NOT_FOUND, "not_found", "Resource not found")


def audit(
    db: Session,
    principal: Principal,
    action: str,
    target_type: str,
    target_id: str,
    request_id: str | None,
    changes: dict[str, Any] | None = None,
    tenant_id: str | None = None,
) -> None:
    db.add(
        AuditEvent(
            tenant_id=tenant_id or principal.tenant_id,
            actor_id=principal.subject,
            actor_type=principal.actor_type,
            action=action,
            target_type=target_type,
            target_id=target_id,
            request_id=request_id,
            changes=changes or {},
        )
    )


def get_application(db: Session, app_id: str, principal: Principal) -> Application:
    app = db.get(Application, app_id)
    if not app:
        fail(404, "application_not_found", "Application not found")
    ensure_tenant(principal, app.tenant_id)
    return app


def validate_json_schema(schema: dict[str, Any]) -> None:
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        fail(422, "invalid_json_schema", exc.message)


def compatibility_errors(
    previous: dict[str, Any], candidate: dict[str, Any], mode: str
) -> list[str]:
    if mode == "none":
        return []
    errors: list[str] = []
    previous_props = previous.get("properties", {})
    candidate_props = candidate.get("properties", {})
    previous_required = set(previous.get("required", []))
    candidate_required = set(candidate.get("required", []))
    if mode in {"backward", "full"}:
        newly_required = candidate_required - previous_required
        if newly_required:
            errors.append(
                f"New required properties are not backward compatible: {sorted(newly_required)}"
            )
        removed = set(previous_props) - set(candidate_props)
        if removed:
            errors.append(f"Removed properties are not backward compatible: {sorted(removed)}")
    if mode in {"forward", "full"}:
        no_longer_required = previous_required - candidate_required
        if no_longer_required:
            errors.append(
                f"Required properties removed by candidate are not forward compatible: "
                f"{sorted(no_longer_required)}"
            )
    for name in set(previous_props) & set(candidate_props):
        old_type = previous_props[name].get("type")
        new_type = candidate_props[name].get("type")
        if old_type and new_type and old_type != new_type:
            errors.append(f"Property {name!r} changed type from {old_type!r} to {new_type!r}")
    return errors


@router.post("/tenants", response_model=TenantRead, status_code=201)
def create_tenant(
    body: TenantCreate,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("apps:write")),
) -> Tenant:
    if "*" not in principal.permissions:
        fail(403, "permission_denied", "Only platform administrators can create tenants")
    tenant = Tenant(name=body.name, slug=body.slug)
    db.add(tenant)
    try:
        db.flush()
        audit(
            db,
            principal,
            "tenant.created",
            "tenant",
            tenant.id,
            request.state.request_id,
            body.model_dump(),
            tenant.id,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        fail(409, "tenant_slug_exists", "Tenant slug already exists")
    return tenant


@router.get("/tenants", response_model=Page)
def list_tenants(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("apps:read")),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page:
    query = select(Tenant)
    count_query = select(func.count()).select_from(Tenant)
    if "*" not in principal.permissions:
        if not principal.tenant_id:
            return Page(items=[], total=0, limit=limit, offset=offset)
        query = query.where(Tenant.id == principal.tenant_id)
        count_query = count_query.where(Tenant.id == principal.tenant_id)
    items = list(db.scalars(query.order_by(Tenant.created_at.desc()).limit(limit).offset(offset)))
    return Page(
        items=[TenantRead.model_validate(item).model_dump(mode="json") for item in items],
        total=db.scalar(count_query) or 0,
        limit=limit,
        offset=offset,
    )


@router.get("/tenants/{tenant_id}", response_model=TenantRead)
def read_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("apps:read")),
) -> Tenant:
    ensure_tenant(principal, tenant_id)
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        fail(404, "tenant_not_found", "Tenant not found")
    return tenant


@router.patch("/tenants/{tenant_id}", response_model=TenantRead)
def update_tenant(
    tenant_id: str,
    body: TenantUpdate,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("apps:write")),
) -> Tenant:
    ensure_tenant(principal, tenant_id)
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        fail(404, "tenant_not_found", "Tenant not found")
    changes = body.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(tenant, key, value)
    audit(db, principal, "tenant.updated", "tenant", tenant.id, request.state.request_id, changes)
    db.commit()
    return tenant


@router.post("/tenants/{tenant_id}/actions/{action}", response_model=TenantRead)
def transition_tenant(
    tenant_id: str,
    action: str,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("apps:write")),
) -> Tenant:
    if action not in {"disable", "archive"}:
        fail(404, "not_found", "Action not found")
    ensure_tenant(principal, tenant_id)
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        fail(404, "tenant_not_found", "Tenant not found")
    tenant.status = Lifecycle.DISABLED if action == "disable" else Lifecycle.ARCHIVED
    audit(
        db,
        principal,
        f"tenant.{action}d",
        "tenant",
        tenant.id,
        request.state.request_id,
    )
    db.commit()
    return tenant


@router.post("/tenants/{tenant_id}/apps", response_model=ApplicationRead, status_code=201)
def create_application(
    tenant_id: str,
    body: ApplicationCreate,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("apps:write")),
) -> Application:
    ensure_tenant(principal, tenant_id)
    if not db.get(Tenant, tenant_id):
        fail(404, "tenant_not_found", "Tenant not found")
    app = Application(tenant_id=tenant_id, **body.model_dump())
    db.add(app)
    try:
        db.flush()
        audit(
            db,
            principal,
            "application.created",
            "application",
            app.id,
            request.state.request_id,
            body.model_dump(),
            tenant_id,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        fail(409, "application_slug_exists", "Application slug already exists in tenant")
    return app


@router.get("/tenants/{tenant_id}/apps", response_model=Page)
def list_applications(
    tenant_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("apps:read")),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page:
    ensure_tenant(principal, tenant_id)
    query = select(Application).where(Application.tenant_id == tenant_id)
    total = db.scalar(
        select(func.count()).select_from(Application).where(Application.tenant_id == tenant_id)
    )
    items = list(
        db.scalars(query.order_by(Application.created_at.desc()).limit(limit).offset(offset))
    )
    return Page(
        items=[ApplicationRead.model_validate(item).model_dump(mode="json") for item in items],
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.get("/apps/{app_id}", response_model=ApplicationRead)
def read_application(
    app_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("apps:read")),
) -> Application:
    return get_application(db, app_id, principal)


@router.patch("/apps/{app_id}", response_model=ApplicationRead)
def update_application(
    app_id: str,
    body: ApplicationUpdate,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("apps:write")),
) -> Application:
    app = get_application(db, app_id, principal)
    changes = body.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(app, key, value)
    audit(
        db,
        principal,
        "application.updated",
        "application",
        app.id,
        request.state.request_id,
        changes,
        app.tenant_id,
    )
    db.commit()
    return app


@router.post("/apps/{app_id}/actions/{action}", response_model=ApplicationRead)
def transition_application(
    app_id: str,
    action: str,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("apps:write")),
) -> Application:
    if action not in {"disable", "archive"}:
        fail(404, "not_found", "Action not found")
    app = get_application(db, app_id, principal)
    app.status = Lifecycle.DISABLED if action == "disable" else Lifecycle.ARCHIVED
    audit(
        db,
        principal,
        f"application.{action}d",
        "application",
        app.id,
        request.state.request_id,
        tenant_id=app.tenant_id,
    )
    db.commit()
    return app


@router.post("/apps/{app_id}/credentials", response_model=CredentialSecret, status_code=201)
def create_credential(
    app_id: str,
    body: CredentialCreate,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("credentials:rotate")),
    settings: Settings = Depends(get_settings),
) -> CredentialSecret:
    app = get_application(db, app_id, principal)
    invalid = set(body.permissions) - VALID_CREDENTIAL_PERMISSIONS
    if invalid:
        fail(422, "invalid_permissions", f"Unsupported permissions: {sorted(invalid)}")
    raw_key, prefix, salt, digest = generate_api_key(settings)
    credential = ApplicationCredential(
        tenant_id=app.tenant_id,
        application_id=app.id,
        name=body.name,
        key_prefix=prefix,
        secret_salt=salt,
        secret_hash=digest,
        permissions=body.permissions,
        expires_at=body.expires_at,
    )
    db.add(credential)
    db.flush()
    audit(
        db,
        principal,
        "credential.created",
        "application_credential",
        credential.id,
        request.state.request_id,
        {"name": body.name, "permissions": body.permissions, "expires_at": str(body.expires_at)},
        app.tenant_id,
    )
    db.commit()
    return CredentialSecret(
        **CredentialRead.model_validate(credential).model_dump(),
        secret=raw_key,
    )


@router.get("/apps/{app_id}/credentials", response_model=Page)
def list_credentials(
    app_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("apps:read")),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page:
    app = get_application(db, app_id, principal)
    query = select(ApplicationCredential).where(ApplicationCredential.application_id == app.id)
    total = db.scalar(
        select(func.count())
        .select_from(ApplicationCredential)
        .where(ApplicationCredential.application_id == app.id)
    )
    items = list(
        db.scalars(
            query.order_by(ApplicationCredential.created_at.desc()).limit(limit).offset(offset)
        )
    )
    return Page(
        items=[CredentialRead.model_validate(item).model_dump(mode="json") for item in items],
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/credentials/{credential_id}/rotate", response_model=CredentialSecret, status_code=201
)
def rotate_credential(
    credential_id: str,
    body: RotateCredential,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("credentials:rotate")),
    settings: Settings = Depends(get_settings),
) -> CredentialSecret:
    current = db.get(ApplicationCredential, credential_id)
    if not current:
        fail(404, "credential_not_found", "Credential not found")
    ensure_tenant(principal, current.tenant_id)
    raw_key, prefix, salt, digest = generate_api_key(settings)
    replacement = ApplicationCredential(
        tenant_id=current.tenant_id,
        application_id=current.application_id,
        name=f"{current.name} (rotated)",
        key_prefix=prefix,
        secret_salt=salt,
        secret_hash=digest,
        permissions=current.permissions,
        expires_at=current.expires_at,
    )
    db.add(replacement)
    db.flush()
    current.replaced_by_id = replacement.id
    current.overlap_ends_at = datetime.now(UTC) + timedelta(seconds=body.overlap_seconds)
    if body.overlap_seconds == 0:
        current.revoked_at = datetime.now(UTC)
    audit(
        db,
        principal,
        "credential.rotated",
        "application_credential",
        current.id,
        request.state.request_id,
        {"replacement_id": replacement.id, "overlap_seconds": body.overlap_seconds},
        current.tenant_id,
    )
    db.commit()
    return CredentialSecret(
        **CredentialRead.model_validate(replacement).model_dump(),
        secret=raw_key,
    )


@router.post("/credentials/{credential_id}/revoke", response_model=CredentialRead)
def revoke_credential(
    credential_id: str,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("credentials:rotate")),
) -> ApplicationCredential:
    credential = db.get(ApplicationCredential, credential_id)
    if not credential:
        fail(404, "credential_not_found", "Credential not found")
    ensure_tenant(principal, credential.tenant_id)
    credential.revoked_at = datetime.now(UTC)
    audit(
        db,
        principal,
        "credential.revoked",
        "application_credential",
        credential.id,
        request.state.request_id,
        tenant_id=credential.tenant_id,
    )
    db.commit()
    return credential


@router.post("/apps/{app_id}/events", response_model=EventRead, status_code=201)
def create_event(
    app_id: str,
    body: EventCreate,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("events:manage")),
) -> Event:
    app = get_application(db, app_id, principal)
    validate_json_schema(body.json_schema)
    event = Event(
        tenant_id=app.tenant_id,
        application_id=app.id,
        event_key=body.event_key,
        allowed_channels=body.allowed_channels,
        recipient_policy=body.recipient_policy,
    )
    db.add(event)
    try:
        db.flush()
        db.add(
            EventSchemaVersion(
                tenant_id=app.tenant_id,
                event_id=event.id,
                version=1,
                schema=body.json_schema,
                compatibility=body.compatibility,
            )
        )
        audit(
            db,
            principal,
            "event.created",
            "event",
            event.id,
            request.state.request_id,
            {"event_key": body.event_key},
            app.tenant_id,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        fail(409, "event_key_exists", "Event key already exists for application")
    return event


@router.get("/apps/{app_id}/events", response_model=Page)
def list_events(
    app_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("apps:read")),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page:
    app = get_application(db, app_id, principal)
    query = select(Event).where(Event.application_id == app.id)
    total = db.scalar(select(func.count()).select_from(Event).where(Event.application_id == app.id))
    items = list(db.scalars(query.order_by(Event.created_at.desc()).limit(limit).offset(offset)))
    return Page(
        items=[EventRead.model_validate(item).model_dump(mode="json") for item in items],
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.get("/events/{event_id}", response_model=EventRead)
def read_event(
    event_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("apps:read")),
) -> Event:
    event = db.get(Event, event_id)
    if not event:
        fail(404, "event_not_found", "Event not found")
    ensure_tenant(principal, event.tenant_id)
    return event


@router.patch("/events/{event_id}", response_model=EventRead)
def update_event(
    event_id: str,
    body: EventUpdate,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("events:manage")),
) -> Event:
    event = db.get(Event, event_id)
    if not event:
        fail(404, "event_not_found", "Event not found")
    ensure_tenant(principal, event.tenant_id)
    changes = body.model_dump(exclude_unset=True, exclude={"json_schema", "compatibility"})
    for key, value in changes.items():
        setattr(event, key, value)
    if body.json_schema is not None:
        validate_json_schema(body.json_schema)
        current = db.scalar(
            select(EventSchemaVersion).where(
                EventSchemaVersion.event_id == event.id,
                EventSchemaVersion.version == event.current_schema_version,
            )
        )
        if current:
            errors = compatibility_errors(current.schema, body.json_schema, body.compatibility)
            if errors:
                fail(409, "schema_incompatible", "; ".join(errors))
        event.current_schema_version += 1
        db.add(
            EventSchemaVersion(
                tenant_id=event.tenant_id,
                event_id=event.id,
                version=event.current_schema_version,
                schema=body.json_schema,
                compatibility=body.compatibility,
            )
        )
        changes["schema_version"] = event.current_schema_version
    audit(
        db,
        principal,
        "event.updated",
        "event",
        event.id,
        request.state.request_id,
        changes,
        event.tenant_id,
    )
    db.commit()
    return event


@router.post("/events/{event_id}/disable", response_model=EventRead)
def disable_event(
    event_id: str,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("events:manage")),
) -> Event:
    event = db.get(Event, event_id)
    if not event:
        fail(404, "event_not_found", "Event not found")
    ensure_tenant(principal, event.tenant_id)
    event.status = Lifecycle.DISABLED
    audit(
        db,
        principal,
        "event.disabled",
        "event",
        event.id,
        request.state.request_id,
        tenant_id=event.tenant_id,
    )
    db.commit()
    return event


@router.get("/events/{event_id}/schemas", response_model=Page)
def list_schema_versions(
    event_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("apps:read")),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page:
    event = db.get(Event, event_id)
    if not event:
        fail(404, "event_not_found", "Event not found")
    ensure_tenant(principal, event.tenant_id)
    query = select(EventSchemaVersion).where(EventSchemaVersion.event_id == event.id)
    total = db.scalar(
        select(func.count())
        .select_from(EventSchemaVersion)
        .where(EventSchemaVersion.event_id == event.id)
    )
    items = list(
        db.scalars(query.order_by(EventSchemaVersion.version.desc()).limit(limit).offset(offset))
    )
    return Page(
        items=[SchemaVersionRead.model_validate(item).model_dump(mode="json") for item in items],
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.post("/notifications", response_model=NotificationRead, status_code=202)
def create_notification(
    body: NotificationCreate,
    request: Request,
    idempotency_key: str = Header(min_length=1, max_length=200, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_app_principal),
) -> Notification:
    if not principal.can("notifications:send"):
        fail(403, "permission_denied", "Credential cannot send notifications")
    app_id = principal.application_id
    if body.app_id and body.app_id != principal.application_id:
        fail(
            403,
            "application_scope_mismatch",
            "Credential does not belong to requested application",
        )
    if not app_id:
        fail(403, "application_scope_missing", "Credential is not scoped to an application")
    app = db.get(Application, app_id)
    if not app or app.status != Lifecycle.ACTIVE:
        fail(404, "application_not_found", "Active application not found")
    event = db.scalar(
        select(Event).where(
            Event.application_id == app.id,
            Event.event_key == body.event_key,
            Event.status == Lifecycle.ACTIVE,
        )
    )
    if not event:
        fail(404, "event_not_found", "Active event not found")
    if body.channel not in event.allowed_channels:
        fail(422, "channel_not_allowed", "Channel is not allowed for this event")
    required_recipient_key = CHANNEL_RECIPIENT_KEYS[body.channel]
    if not body.recipient.get(required_recipient_key):
        fail(422, "invalid_recipient", f"Recipient requires {required_recipient_key!r}")
    schema_version = db.scalar(
        select(EventSchemaVersion).where(
            EventSchemaVersion.event_id == event.id,
            EventSchemaVersion.version == event.current_schema_version,
        )
    )
    if not schema_version:
        fail(500, "schema_missing", "Current event schema is unavailable")
    try:
        Draft202012Validator(schema_version.schema).validate(body.data)
    except ValidationError as exc:
        fail(422, "event_data_invalid", exc.message)
    try:
        delivery = resolve_delivery(
            db,
            app,
            event,
            body.channel,
            body.locale,
            body.variant,
            get_settings().platform_default_locale,
        )
    except ResolutionError as exc:
        fail(409, exc.code, str(exc))
    payload = body.model_dump(mode="json")
    fingerprint = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    existing = db.scalar(
        select(Notification).where(
            Notification.application_id == app.id,
            Notification.idempotency_key == idempotency_key,
        )
    )
    if existing:
        if existing.request_fingerprint != fingerprint:
            fail(409, "idempotency_conflict", "Key was already used with a different request")
        return existing
    try:
        consume_quota(db, app, body.channel)
    except QuotaExceeded as exc:
        db.rollback()
        fail(429, "quota_exceeded", str(exc))
    now = datetime.now(UTC)
    notification = Notification(
        tenant_id=app.tenant_id,
        application_id=app.id,
        event_id=event.id,
        event_key=event.event_key,
        channel=body.channel,
        recipient=body.recipient,
        event_data=body.data,
        metadata_json=body.metadata,
        locale=body.locale or app.default_locale,
        variant=body.variant or "default",
        priority=body.priority,
        correlation_id=body.metadata.get("correlation_id") or request.state.request_id,
        idempotency_key=idempotency_key,
        request_fingerprint=fingerprint,
        scheduled_at=body.scheduled_at,
        status=NotificationStatus.ACCEPTED,
        template_version_id=delivery.template_version.id,
        provider_config_id=delivery.provider.id,
    )
    db.add(notification)
    try:
        db.flush()
        db.add(
            OutboxEvent(
                tenant_id=app.tenant_id,
                aggregate_type="notification",
                aggregate_id=notification.id,
                event_type=(
                    "notification.scheduled"
                    if body.scheduled_at and body.scheduled_at > now
                    else "notification.accepted"
                ),
                payload={
                    "notification_id": notification.id,
                    "channel": notification.channel,
                    **(
                        {"available_at": body.scheduled_at.isoformat()}
                        if body.scheduled_at and body.scheduled_at > now
                        else {}
                    ),
                },
            )
        )
        audit(
            db,
            principal,
            "notification.accepted",
            "notification",
            notification.id,
            request.state.request_id,
            {"channel": notification.channel, "event_key": notification.event_key},
            app.tenant_id,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(Notification).where(
                Notification.application_id == app.id,
                Notification.idempotency_key == idempotency_key,
            )
        )
        if existing and existing.request_fingerprint == fingerprint:
            return existing
        fail(409, "idempotency_conflict", "Key was already used with a different request")
    return notification


@router.get("/notifications/{notification_id}", response_model=NotificationRead)
def read_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_app_principal),
) -> Notification:
    notification = db.get(Notification, notification_id)
    if (
        not notification
        or notification.application_id != principal.application_id
        or not principal.can("notifications:read")
    ):
        fail(404, "notification_not_found", "Notification not found")
    return notification


@router.post("/notifications/{notification_id}/cancel", response_model=NotificationRead)
def cancel_notification(
    notification_id: str,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_app_principal),
) -> Notification:
    notification = db.get(Notification, notification_id)
    if (
        not notification
        or notification.application_id != principal.application_id
        or not principal.can("notifications:cancel")
    ):
        fail(404, "notification_not_found", "Notification not found")
    if notification.status not in {NotificationStatus.ACCEPTED, NotificationStatus.QUEUED}:
        fail(409, "notification_not_cancellable", "Notification is already processing or final")
    notification.status = NotificationStatus.CANCELLED
    notification.cancelled_at = datetime.now(UTC)
    audit(
        db,
        principal,
        "notification.cancelled",
        "notification",
        notification.id,
        request.state.request_id,
        tenant_id=notification.tenant_id,
    )
    db.commit()
    return notification


@router.get("/audits", response_model=Page)
def list_audits(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("audit:read")),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page:
    query = select(AuditEvent)
    count_query = select(func.count()).select_from(AuditEvent)
    if "*" not in principal.permissions:
        query = query.where(AuditEvent.tenant_id == principal.tenant_id)
        count_query = count_query.where(AuditEvent.tenant_id == principal.tenant_id)
    items = list(
        db.scalars(query.order_by(AuditEvent.created_at.desc()).limit(limit).offset(offset))
    )
    return Page(
        items=[
            {
                "id": item.id,
                "tenant_id": item.tenant_id,
                "actor_id": item.actor_id,
                "actor_type": item.actor_type,
                "action": item.action,
                "target_type": item.target_type,
                "target_id": item.target_id,
                "request_id": item.request_id,
                "changes": item.changes,
                "created_at": item.created_at.isoformat(),
            }
            for item in items
        ],
        total=db.scalar(count_query) or 0,
        limit=limit,
        offset=offset,
    )
