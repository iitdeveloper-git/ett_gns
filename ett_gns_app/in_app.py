from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import jwt
from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from ett_gns_app.api import audit, fail, get_application
from ett_gns_app.database import get_db
from ett_gns_app.models import (
    InAppConnection,
    InAppDeliveryAttempt,
    InAppNotification,
    InAppPreference,
    InAppRecipient,
    Notification,
    NotificationStatus,
    TemplateVersion,
)
from ett_gns_app.schemas import (
    InAppAck,
    InAppAdminTest,
    InAppNotificationRead,
    InAppPreferenceRead,
    InAppPreferenceUpdate,
    InAppUnreadCount,
    NotificationCreate,
    Page,
)
from ett_gns_app.security import Principal, get_app_principal, require
from ett_gns_app.settings import Settings, get_settings
from ett_gns_app.template_service import render_content

router = APIRouter(prefix="/api/v1")
SEVERITIES = {"info", "success", "warning", "error", "critical"}
RECIPIENT_TYPES = {"user", "users", "role", "group", "tenant", "application"}


@dataclass(frozen=True)
class InAppUserPrincipal:
    subject: str
    tenant_id: str
    application_id: str
    session_id: str
    roles: frozenset[str]
    groups: frozenset[str]


class LocalInAppHub:
    def __init__(self) -> None:
        self._subscribers: dict[tuple[str, str, str], set[asyncio.Queue[dict[str, Any]]]] = {}

    def subscribe(self, tenant_id: str, application_id: str, user_id: str) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=100)
        self._subscribers.setdefault((tenant_id, application_id, user_id), set()).add(queue)
        return queue

    def unsubscribe(
        self, tenant_id: str, application_id: str, user_id: str, queue: asyncio.Queue[dict[str, Any]]
    ) -> None:
        subscribers = self._subscribers.get((tenant_id, application_id, user_id))
        if subscribers:
            subscribers.discard(queue)
            if not subscribers:
                self._subscribers.pop((tenant_id, application_id, user_id), None)

    def active_count(self) -> int:
        return sum(len(value) for value in self._subscribers.values())

    def publish(self, tenant_id: str, application_id: str, user_ids: set[str], event: dict[str, Any]) -> None:
        for user_id in user_ids:
            for queue in list(self._subscribers.get((tenant_id, application_id, user_id), set())):
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    continue


HUB = LocalInAppHub()


def sse(event: str, event_id: str, data: dict[str, Any]) -> str:
    return f"event: {event}\nid: {event_id}\ndata: {json.dumps(data, default=str, separators=(',', ':'))}\n\n"


def user_principal(
    request: Request,
    settings: Settings = Depends(get_settings),
    authorization: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None),
    x_app_id: str | None = Header(default=None),
    x_session_id: str | None = Header(default=None),
    x_gns_user_roles: str | None = Header(default=None),
    x_gns_user_groups: str | None = Header(default=None),
) -> InAppUserPrincipal:
    if not authorization or not authorization.startswith("Bearer "):
        fail(401, "identity_required", "In-app user bearer token required")
    token = authorization.removeprefix("Bearer ")
    if settings.allow_dev_identity and settings.environment in {"development", "test"}:
        if not token.startswith("dev_user_") or not x_tenant_id or not x_app_id:
            fail(401, "identity_required", "Development in-app identity is incomplete")
        return InAppUserPrincipal(
            subject=token.removeprefix("dev_user_"),
            tenant_id=x_tenant_id,
            application_id=x_app_id,
            session_id=x_session_id or f"ses_{uuid4().hex}",
            roles=frozenset(role.strip() for role in (x_gns_user_roles or "").split(",") if role),
            groups=frozenset(group.strip() for group in (x_gns_user_groups or "").split(",") if group),
        )
    if not settings.oidc_issuer or not settings.oidc_audience:
        fail(501, "oidc_not_configured", "OIDC verifier is not configured")
    try:
        jwks_client = jwt.PyJWKClient(
            f"{settings.oidc_issuer.rstrip('/')}/.well-known/jwks.json",
            cache_keys=True,
        )
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience=settings.oidc_audience,
            issuer=settings.oidc_issuer,
            options={"require": ["exp", "iat", "iss", "sub"]},
        )
    except jwt.PyJWTError:
        fail(401, "oidc_token_invalid", "OIDC token validation failed")
    tenant_id = claims.get("tenant_id")
    application_id = claims.get("application_id")
    if not tenant_id or not application_id:
        fail(403, "scope_missing", "Token must include tenant_id and application_id")
    return InAppUserPrincipal(
        subject=str(claims["sub"]),
        tenant_id=str(tenant_id),
        application_id=str(application_id),
        session_id=str(claims.get("sid") or claims.get("session_id") or f"ses_{uuid4().hex}"),
        roles=frozenset(str(role) for role in claims.get("roles", [])),
        groups=frozenset(str(group) for group in claims.get("groups", [])),
    )


def active_filter(now: datetime) -> tuple[Any, ...]:
    return (
        InAppNotification.archived_at.is_(None),
        or_(InAppNotification.expires_at.is_(None), InAppNotification.expires_at > now),
        InAppRecipient.archived_at.is_(None),
        InAppRecipient.dismissed_at.is_(None),
    )


def recipient_visibility(principal: InAppUserPrincipal) -> Any:
    return or_(
        and_(InAppRecipient.recipient_type == "user", InAppRecipient.recipient_id == principal.subject),
        and_(InAppRecipient.recipient_type == "tenant", InAppRecipient.recipient_id == principal.tenant_id),
        and_(
            InAppRecipient.recipient_type == "application",
            InAppRecipient.recipient_id == principal.application_id,
        ),
        and_(InAppRecipient.recipient_type == "role", InAppRecipient.recipient_id.in_(principal.roles or {""})),
        and_(
            InAppRecipient.recipient_type == "group",
            InAppRecipient.recipient_id.in_(principal.groups or {""}),
        ),
    )


def serialize(notification: InAppNotification, recipient: InAppRecipient) -> dict[str, Any]:
    return InAppNotificationRead(
        id=notification.id,
        event_key=notification.event_key,
        title=notification.title,
        message=notification.message,
        severity=notification.severity,
        priority=notification.priority,
        action_payload=notification.action_payload,
        toast_payload=notification.toast_payload,
        metadata_json=notification.metadata_json,
        expires_at=notification.expires_at,
        created_at=notification.created_at,
        read=recipient.read_at is not None,
        recipient_id=recipient.id,
        read_at=recipient.read_at,
        dismissed_at=recipient.dismissed_at,
        opened_at=recipient.opened_at,
    ).model_dump(mode="json")


def safe_action(action: Any) -> dict[str, Any]:
    if not action:
        return {}
    if not isinstance(action, dict):
        fail(422, "in_app_action_invalid", "Action must be an object")
    url = str(action.get("url", ""))
    if not url.startswith("/") or url.startswith("//") or "javascript:" in url.lower():
        fail(422, "in_app_action_invalid", "Action URL must be a safe relative deep link")
    return {
        "label": str(action.get("label", "Open"))[:80],
        "url": url[:500],
        "type": "deep_link",
    }


def recipient_targets(recipient: dict[str, Any], tenant_id: str, application_id: str) -> list[tuple[str, str]]:
    recipient_type = recipient.get("type")
    if recipient_type not in RECIPIENT_TYPES:
        fail(422, "in_app_recipient_invalid", "Unsupported in-app recipient type")
    if recipient_type == "user":
        recipient_id = str(recipient.get("id") or "")
        if not recipient_id:
            fail(422, "in_app_recipient_invalid", "User recipient requires id")
        return [("user", recipient_id)]
    if recipient_type == "users":
        ids = recipient.get("ids")
        if not isinstance(ids, list) or not ids or len(ids) > 1000:
            fail(422, "in_app_recipient_invalid", "Users recipient requires 1-1000 ids")
        return [("user", str(value)) for value in ids]
    if recipient_type in {"role", "group"}:
        recipient_id = str(recipient.get("id") or "")
        if not recipient_id:
            fail(422, "in_app_recipient_invalid", f"{recipient_type} recipient requires id")
        return [(recipient_type, recipient_id)]
    if recipient_type == "tenant":
        return [("tenant", tenant_id)]
    return [("application", application_id)]


def preference_allows(db: Session, notification: Notification, recipient_type: str, recipient_id: str) -> bool:
    if recipient_type != "user":
        return True
    pref = db.scalar(
        select(InAppPreference).where(
            InAppPreference.tenant_id == notification.tenant_id,
            InAppPreference.application_id == notification.application_id,
            InAppPreference.user_id == recipient_id,
            InAppPreference.event_key.in_([notification.event_key, "*"]),
        )
    )
    if not pref:
        return True
    return pref.in_app_enabled and notification.priority >= pref.minimum_priority


def create_in_app_delivery(db: Session, notification: Notification) -> InAppNotification:
    version = db.get(TemplateVersion, notification.template_version_id)
    if not version:
        fail(500, "template_missing", "In-app template version is unavailable")
    content = render_content(version.content, notification.event_data)
    severity = str(content.get("severity", "info"))
    if severity not in SEVERITIES:
        fail(422, "in_app_template_invalid", "Invalid in-app severity")
    action = safe_action(content.get("action"))
    toast = content.get("toast") if isinstance(content.get("toast"), dict) else {}
    expires_at_raw = notification.metadata_json.get("expires_at")
    expires_at = None
    if expires_at_raw:
        expires_at = datetime.fromisoformat(str(expires_at_raw).replace("Z", "+00:00"))
    dedup_key = notification.metadata_json.get("deduplication_key")
    fingerprint = hashlib.sha256(
        json.dumps(
            {
                "title": content.get("title"),
                "message": content.get("message"),
                "action": action,
                "recipient": notification.recipient,
                "data": notification.event_data,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    if dedup_key:
        existing = db.scalar(
            select(InAppNotification).where(
                InAppNotification.tenant_id == notification.tenant_id,
                InAppNotification.application_id == notification.application_id,
                InAppNotification.deduplication_key == str(dedup_key),
            )
        )
        if existing:
            if existing.request_fingerprint != fingerprint:
                fail(409, "in_app_deduplication_conflict", "Deduplication key has different payload")
            return existing
    in_app = InAppNotification(
        tenant_id=notification.tenant_id,
        application_id=notification.application_id,
        source_notification_id=notification.id,
        event_key=notification.event_key,
        template_version_id=notification.template_version_id,
        title=str(content["title"])[:240],
        message=str(content["message"])[:4000],
        severity=severity,
        priority=notification.priority,
        action_payload=action,
        toast_payload=toast or {"enabled": True, "auto_dismiss_ms": 6000},
        metadata_json=notification.metadata_json,
        expires_at=expires_at,
        deduplication_key=str(dedup_key) if dedup_key else None,
        request_fingerprint=fingerprint,
        correlation_id=notification.correlation_id,
    )
    db.add(in_app)
    db.flush()
    visible_user_ids: set[str] = set()
    for recipient_type, recipient_id in recipient_targets(
        notification.recipient, notification.tenant_id, notification.application_id
    ):
        if not preference_allows(db, notification, recipient_type, recipient_id):
            continue
        recipient = InAppRecipient(
            notification_id=in_app.id,
            tenant_id=notification.tenant_id,
            application_id=notification.application_id,
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            delivery_status="queued",
        )
        db.add(recipient)
        db.flush()
        db.add(
            InAppDeliveryAttempt(
                tenant_id=notification.tenant_id,
                notification_recipient_id=recipient.id,
                attempt_number=1,
                transport="sse",
                status="queued",
                completed_at=datetime.now(UTC),
            )
        )
        if recipient_type == "user":
            visible_user_ids.add(recipient_id)
    notification.status = NotificationStatus.DELIVERED
    notification.failure_code = None
    db.flush()
    # Broadcast targets remain source-of-truth rows; IAM expansion is an external integration.
    first_recipient = db.scalar(select(InAppRecipient).where(InAppRecipient.notification_id == in_app.id))
    if first_recipient and visible_user_ids:
        payload = {"notification": serialize(in_app, first_recipient)}
        HUB.publish(notification.tenant_id, notification.application_id, visible_user_ids, payload)
    return in_app


def find_visible_recipient(
    db: Session, notification_id: str, principal: InAppUserPrincipal
) -> tuple[InAppNotification, InAppRecipient]:
    row = db.execute(
        select(InAppNotification, InAppRecipient)
        .join(InAppRecipient, InAppRecipient.notification_id == InAppNotification.id)
        .where(
            InAppNotification.id == notification_id,
            InAppNotification.tenant_id == principal.tenant_id,
            InAppNotification.application_id == principal.application_id,
            recipient_visibility(principal),
        )
    ).first()
    if not row:
        fail(404, "in_app_notification_not_found", "Notification not found")
    return row[0], row[1]


@router.get("/in-app/notifications", response_model=Page)
def list_in_app_notifications(
    db: Session = Depends(get_db),
    principal: InAppUserPrincipal = Depends(user_principal),
    unread_only: bool = False,
    severity: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page:
    now = datetime.now(UTC)
    conditions: list[Any] = [
        InAppNotification.tenant_id == principal.tenant_id,
        InAppNotification.application_id == principal.application_id,
        recipient_visibility(principal),
        *active_filter(now),
    ]
    if unread_only:
        conditions.append(InAppRecipient.read_at.is_(None))
    if severity:
        conditions.append(InAppNotification.severity == severity)
    if search:
        like = f"%{search}%"
        conditions.append(or_(InAppNotification.title.ilike(like), InAppNotification.message.ilike(like)))
    base = (
        select(InAppNotification, InAppRecipient)
        .join(InAppRecipient, InAppRecipient.notification_id == InAppNotification.id)
        .where(*conditions)
    )
    rows = list(
        db.execute(
            base.order_by(InAppNotification.priority.desc(), InAppNotification.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    total = db.scalar(
        select(func.count())
        .select_from(InAppRecipient)
        .join(InAppNotification, InAppRecipient.notification_id == InAppNotification.id)
        .where(*conditions)
    )
    return Page(
        items=[serialize(notification, recipient) for notification, recipient in rows],
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.get("/in-app/notifications/{notification_id}", response_model=InAppNotificationRead)
def read_in_app_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    principal: InAppUserPrincipal = Depends(user_principal),
) -> dict[str, Any]:
    notification, recipient = find_visible_recipient(db, notification_id, principal)
    return serialize(notification, recipient)


@router.post("/in-app/notifications/{notification_id}/ack", response_model=InAppNotificationRead)
def ack_in_app_notification(
    notification_id: str,
    body: InAppAck,
    db: Session = Depends(get_db),
    principal: InAppUserPrincipal = Depends(user_principal),
) -> dict[str, Any]:
    notification, recipient = find_visible_recipient(db, notification_id, principal)
    now = datetime.now(UTC)
    if body.status == "delivered":
        recipient.delivered_at = recipient.delivered_at or now
    elif body.status == "displayed":
        recipient.displayed_at = recipient.displayed_at or now
    elif body.status == "opened":
        recipient.opened_at = recipient.opened_at or now
        recipient.read_at = recipient.read_at or now
    recipient.delivery_status = body.status
    recipient.delivery_attempt_count += 1
    db.add(
        InAppDeliveryAttempt(
            tenant_id=recipient.tenant_id,
            notification_recipient_id=recipient.id,
            attempt_number=recipient.delivery_attempt_count,
            transport="sdk",
            status=body.status,
            completed_at=now,
        )
    )
    db.commit()
    HUB.publish(principal.tenant_id, principal.application_id, {principal.subject}, {"notification": serialize(notification, recipient)})
    return serialize(notification, recipient)


def set_read_state(
    notification_id: str,
    read: bool,
    db: Session,
    principal: InAppUserPrincipal,
) -> dict[str, Any]:
    notification, recipient = find_visible_recipient(db, notification_id, principal)
    recipient.read_at = datetime.now(UTC) if read else None
    db.commit()
    payload = serialize(notification, recipient)
    HUB.publish(principal.tenant_id, principal.application_id, {principal.subject}, {"notification": payload})
    return payload


@router.post("/in-app/notifications/{notification_id}/read", response_model=InAppNotificationRead)
def mark_in_app_read(
    notification_id: str,
    db: Session = Depends(get_db),
    principal: InAppUserPrincipal = Depends(user_principal),
) -> dict[str, Any]:
    return set_read_state(notification_id, True, db, principal)


@router.post("/in-app/notifications/{notification_id}/unread", response_model=InAppNotificationRead)
def mark_in_app_unread(
    notification_id: str,
    db: Session = Depends(get_db),
    principal: InAppUserPrincipal = Depends(user_principal),
) -> dict[str, Any]:
    return set_read_state(notification_id, False, db, principal)


@router.post("/in-app/notifications/{notification_id}/dismiss", response_model=InAppNotificationRead)
def dismiss_in_app_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    principal: InAppUserPrincipal = Depends(user_principal),
) -> dict[str, Any]:
    notification, recipient = find_visible_recipient(db, notification_id, principal)
    recipient.dismissed_at = datetime.now(UTC)
    db.commit()
    return serialize(notification, recipient)


@router.post("/in-app/notifications/read-all", response_model=InAppUnreadCount)
def mark_all_in_app_read(
    db: Session = Depends(get_db),
    principal: InAppUserPrincipal = Depends(user_principal),
) -> InAppUnreadCount:
    rows = list(
        db.scalars(
            select(InAppRecipient)
            .join(InAppNotification, InAppRecipient.notification_id == InAppNotification.id)
            .where(
                InAppNotification.tenant_id == principal.tenant_id,
                InAppNotification.application_id == principal.application_id,
                recipient_visibility(principal),
                InAppRecipient.read_at.is_(None),
                *active_filter(datetime.now(UTC)),
            )
        )
    )
    now = datetime.now(UTC)
    for recipient in rows:
        recipient.read_at = now
    db.commit()
    return InAppUnreadCount(unread=0)


@router.get("/in-app/unread-count", response_model=InAppUnreadCount)
def unread_count(
    db: Session = Depends(get_db),
    principal: InAppUserPrincipal = Depends(user_principal),
) -> InAppUnreadCount:
    total = db.scalar(
        select(func.count())
        .select_from(InAppRecipient)
        .join(InAppNotification, InAppRecipient.notification_id == InAppNotification.id)
        .where(
            InAppNotification.tenant_id == principal.tenant_id,
            InAppNotification.application_id == principal.application_id,
            recipient_visibility(principal),
            InAppRecipient.read_at.is_(None),
            *active_filter(datetime.now(UTC)),
        )
    )
    return InAppUnreadCount(unread=total or 0)


@router.get("/in-app/preferences", response_model=Page)
def get_preferences(
    db: Session = Depends(get_db),
    principal: InAppUserPrincipal = Depends(user_principal),
) -> Page:
    prefs = list(
        db.scalars(
            select(InAppPreference).where(
                InAppPreference.tenant_id == principal.tenant_id,
                InAppPreference.application_id == principal.application_id,
                InAppPreference.user_id == principal.subject,
            )
        )
    )
    return Page(
        items=[InAppPreferenceRead.model_validate(pref).model_dump(mode="json") for pref in prefs],
        total=len(prefs),
        limit=len(prefs),
        offset=0,
    )


@router.patch("/in-app/preferences", response_model=InAppPreferenceRead)
def update_preferences(
    body: InAppPreferenceUpdate,
    db: Session = Depends(get_db),
    principal: InAppUserPrincipal = Depends(user_principal),
) -> InAppPreference:
    pref = db.scalar(
        select(InAppPreference).where(
            InAppPreference.tenant_id == principal.tenant_id,
            InAppPreference.application_id == principal.application_id,
            InAppPreference.user_id == principal.subject,
            InAppPreference.event_key == body.event_key,
        )
    )
    if not pref:
        pref = InAppPreference(
            tenant_id=principal.tenant_id,
            application_id=principal.application_id,
            user_id=principal.subject,
            event_key=body.event_key,
        )
        db.add(pref)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(pref, key, value)
    db.commit()
    return pref


@router.get("/in-app/stream")
async def stream_in_app_notifications(
    request: Request,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    db: Session = Depends(get_db),
    principal: InAppUserPrincipal = Depends(user_principal),
) -> StreamingResponse:
    connection_id = f"con_{uuid4().hex}"
    connection = InAppConnection(
        connection_id=connection_id,
        tenant_id=principal.tenant_id,
        application_id=principal.application_id,
        user_id=principal.subject,
        session_id=principal.session_id,
        transport="sse",
    )
    db.add(connection)
    db.commit()
    queue = HUB.subscribe(principal.tenant_id, principal.application_id, principal.subject)

    async def events() -> AsyncIterator[str]:
        try:
            yield sse("connection.ready", connection_id, {"connection_id": connection_id})
            replay = list_in_app_notifications(db, principal, unread_only=False, limit=25, offset=0)
            for item in replay.items:
                if last_event_id and str(item["id"]) <= last_event_id:
                    continue
                yield sse("notification.created", str(item["id"]), item)
            while not await request.is_disconnected():
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=15)
                    notification = item.get("notification", {})
                    yield sse("notification.updated", str(notification.get("id", uuid4().hex)), notification)
                except TimeoutError:
                    yield sse("heartbeat", f"hb_{uuid4().hex}", {"ts": datetime.now(UTC).isoformat()})
        finally:
            HUB.unsubscribe(principal.tenant_id, principal.application_id, principal.subject, queue)
            connection_row = db.get(InAppConnection, connection_id)
            if connection_row:
                db.delete(connection_row)
                db.commit()

    return StreamingResponse(events(), media_type="text/event-stream")


@router.get("/admin/in-app/notifications", response_model=Page)
def admin_list_in_app(
    tenant_id: str | None = None,
    application_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("notifications:read")),
) -> Page:
    conditions: list[Any] = []
    if "*" not in principal.permissions:
        conditions.append(InAppNotification.tenant_id == principal.tenant_id)
    if tenant_id:
        conditions.append(InAppNotification.tenant_id == tenant_id)
    if application_id:
        conditions.append(InAppNotification.application_id == application_id)
    items = list(
        db.scalars(
            select(InAppNotification)
            .where(*conditions)
            .order_by(InAppNotification.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    total = db.scalar(select(func.count()).select_from(InAppNotification).where(*conditions))
    return Page(
        items=[
            {
                "id": item.id,
                "tenant_id": item.tenant_id,
                "application_id": item.application_id,
                "event_key": item.event_key,
                "title": item.title,
                "severity": item.severity,
                "priority": item.priority,
                "created_at": item.created_at.isoformat(),
            }
            for item in items
        ],
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.get("/admin/in-app/connections", response_model=Page)
def admin_connections(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("notifications:read")),
) -> Page:
    conditions = [] if "*" in principal.permissions else [InAppConnection.tenant_id == principal.tenant_id]
    rows = list(db.scalars(select(InAppConnection).where(*conditions)))
    return Page(
        items=[
            {
                "connection_id": row.connection_id,
                "tenant_id": row.tenant_id,
                "application_id": row.application_id,
                "user_id": row.user_id,
                "session_id": row.session_id,
                "transport": row.transport,
                "connected_at": row.connected_at.isoformat(),
                "last_seen_at": row.last_seen_at.isoformat(),
            }
            for row in rows
        ],
        total=len(rows),
        limit=len(rows),
        offset=0,
    )


@router.get("/admin/in-app/delivery-attempts", response_model=Page)
def admin_delivery_attempts(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("notifications:read")),
    limit: int = 50,
    offset: int = 0,
) -> Page:
    conditions = [] if "*" in principal.permissions else [InAppDeliveryAttempt.tenant_id == principal.tenant_id]
    rows = list(
        db.scalars(
            select(InAppDeliveryAttempt)
            .where(*conditions)
            .order_by(InAppDeliveryAttempt.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    total = db.scalar(select(func.count()).select_from(InAppDeliveryAttempt).where(*conditions))
    return Page(
        items=[
            {
                "id": row.id,
                "notification_recipient_id": row.notification_recipient_id,
                "attempt_number": row.attempt_number,
                "transport": row.transport,
                "status": row.status,
                "error_code": row.error_code,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ],
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.post("/admin/in-app/test", status_code=202)
def admin_test_in_app(
    body: InAppAdminTest,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("notifications:retry")),
    app_principal: Principal = Depends(get_app_principal),
) -> dict[str, str]:
    app = get_application(db, body.application_id, principal)
    if app_principal.application_id != app.id:
        fail(403, "application_scope_mismatch", "Application key must match test app")
    notification_body = NotificationCreate(
        event_key=body.event_key,
        channel="in_app",
        recipient=body.recipient,
        data=body.data,
        priority=body.priority,
        metadata=body.metadata,
    )
    from ett_gns_app.api import create_notification

    created = create_notification(
        notification_body,
        request,
        idempotency_key=f"admin-in-app-test-{uuid4().hex}",
        db=db,
        principal=app_principal,
    )
    audit(
        db,
        principal,
        "in_app.test_sent",
        "notification",
        created.id,
        request.state.request_id,
        tenant_id=app.tenant_id,
    )
    db.commit()
    return {"notification_id": created.id}


def publish_created(notification: InAppNotification, db: Session) -> None:
    user_ids = {
        row.recipient_id
        for row in db.scalars(
            select(InAppRecipient).where(
                InAppRecipient.notification_id == notification.id,
                InAppRecipient.recipient_type == "user",
            )
        )
    }
    if not user_ids:
        return
    recipient = db.scalar(select(InAppRecipient).where(InAppRecipient.notification_id == notification.id))
    if recipient:
        HUB.publish(
            notification.tenant_id,
            notification.application_id,
            user_ids,
            {"notification": serialize(notification, recipient)},
        )
