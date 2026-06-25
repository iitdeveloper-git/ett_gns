from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ett_gns_app.api import audit, ensure_tenant, fail
from ett_gns_app.database import get_db
from ett_gns_app.models import (
    DeliveryAttempt,
    DeliveryEvent,
    Notification,
    NotificationStatus,
    OutboxEvent,
    ProviderConfig,
)
from ett_gns_app.schemas import NotificationRead, Page
from ett_gns_app.security import Principal, require

router = APIRouter(prefix="/api/v1/operations", tags=["operations"])


def get_notification(db: Session, notification_id: str, principal: Principal) -> Notification:
    notification = db.get(Notification, notification_id)
    if not notification:
        fail(404, "notification_not_found", "Notification not found")
    ensure_tenant(principal, notification.tenant_id)
    return notification


@router.get("/dashboard")
def dashboard(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("notifications:read")),
) -> dict[str, object]:
    tenant_condition = (
        [] if "*" in principal.permissions else [Notification.tenant_id == principal.tenant_id]
    )
    status_rows = db.execute(
        select(Notification.status, func.count())
        .where(*tenant_condition)
        .group_by(Notification.status)
    ).all()
    channel_rows = db.execute(
        select(Notification.channel, func.count())
        .where(*tenant_condition)
        .group_by(Notification.channel)
    ).all()
    queue_depth = db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(
            *tenant_condition,
            Notification.status.in_(
                [
                    NotificationStatus.ACCEPTED,
                    NotificationStatus.QUEUED,
                    NotificationStatus.DEFERRED,
                ]
            ),
        )
    )
    provider_query = select(
        ProviderConfig.channel,
        ProviderConfig.name,
        ProviderConfig.health_status,
        ProviderConfig.active,
    )
    if "*" not in principal.permissions:
        provider_query = provider_query.where(ProviderConfig.tenant_id == principal.tenant_id)
    providers = [
        {"channel": row[0], "name": row[1], "health": row[2], "active": row[3]}
        for row in db.execute(provider_query).all()
    ]
    status_counts: dict[str, int] = {str(row[0]): int(row[1]) for row in status_rows}
    channel_counts: dict[str, int] = {str(row[0]): int(row[1]) for row in channel_rows}
    return {
        "volume": sum(count for _, count in status_rows),
        "status_counts": status_counts,
        "channel_counts": channel_counts,
        "queue_depth": queue_depth or 0,
        "retries": status_counts.get(str(NotificationStatus.DEFERRED), 0),
        "dlq": status_counts.get(str(NotificationStatus.DEAD_LETTERED), 0),
        "provider_health": providers,
    }


@router.get("/notifications", response_model=Page)
def list_notifications(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("notifications:read")),
    status_filter: str | None = Query(default=None, alias="status"),
    channel: str | None = None,
    search: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Page:
    query = select(Notification)
    count_query = select(func.count()).select_from(Notification)
    conditions = []
    if "*" not in principal.permissions:
        conditions.append(Notification.tenant_id == principal.tenant_id)
    if status_filter:
        conditions.append(Notification.status == status_filter)
    if channel:
        conditions.append(Notification.channel == channel)
    if search:
        conditions.append(
            or_(
                Notification.id == search,
                Notification.correlation_id == search,
                Notification.event_key.contains(search),
            )
        )
    if conditions:
        query = query.where(*conditions)
        count_query = count_query.where(*conditions)
    items = list(
        db.scalars(query.order_by(Notification.created_at.desc()).limit(limit).offset(offset))
    )
    return Page(
        items=[NotificationRead.model_validate(item).model_dump(mode="json") for item in items],
        total=db.scalar(count_query) or 0,
        limit=limit,
        offset=offset,
    )


@router.get("/notifications/{notification_id}")
def notification_timeline(
    notification_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("notifications:read")),
) -> dict[str, object]:
    notification = get_notification(db, notification_id, principal)
    attempts = list(
        db.scalars(
            select(DeliveryAttempt)
            .where(DeliveryAttempt.notification_id == notification.id)
            .order_by(DeliveryAttempt.attempt_number)
        )
    )
    events = list(
        db.scalars(
            select(DeliveryEvent)
            .where(DeliveryEvent.notification_id == notification.id)
            .order_by(DeliveryEvent.occurred_at)
        )
    )
    redacted_recipient = {
        key: ("***" if key in {"email", "phone", "token", "chat_id"} else value)
        for key, value in notification.recipient.items()
    }
    return {
        "notification": NotificationRead.model_validate(notification).model_dump(mode="json"),
        "recipient": redacted_recipient,
        "attempts": [
            {
                "id": item.id,
                "attempt_number": item.attempt_number,
                "status": item.status,
                "retryable": item.retryable,
                "error_code": item.error_code,
                "provider_message_id": item.provider_message_id,
                "duration_ms": item.duration_ms,
                "created_at": item.created_at.isoformat(),
            }
            for item in attempts
        ],
        "events": [
            {
                "id": item.id,
                "status": item.status,
                "occurred_at": item.occurred_at.isoformat(),
            }
            for item in events
        ],
    }


@router.post("/notifications/{notification_id}/retry", response_model=NotificationRead)
def retry_notification(
    notification_id: str,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("notifications:retry")),
) -> Notification:
    notification = get_notification(db, notification_id, principal)
    if notification.status not in {
        NotificationStatus.FAILED,
        NotificationStatus.DEFERRED,
        NotificationStatus.DEAD_LETTERED,
    }:
        fail(409, "notification_not_retryable", "Notification is not in a retryable state")
    notification.status = NotificationStatus.QUEUED
    notification.next_attempt_at = None
    notification.processing_lease_until = None
    db.add(
        OutboxEvent(
            tenant_id=notification.tenant_id,
            aggregate_type="notification",
            aggregate_id=notification.id,
            event_type="notification.operator_retry",
            payload={"notification_id": notification.id},
        )
    )
    audit(
        db,
        principal,
        "notification.retried",
        "notification",
        notification.id,
        request.state.request_id,
        tenant_id=notification.tenant_id,
    )
    db.commit()
    return notification


@router.post("/notifications/{notification_id}/dlq-replay", response_model=NotificationRead)
def replay_dead_letter(
    notification_id: str,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("notifications:retry")),
) -> Notification:
    notification = get_notification(db, notification_id, principal)
    if notification.status != NotificationStatus.DEAD_LETTERED:
        fail(409, "notification_not_dead_lettered", "Notification is not dead-lettered")
    notification.status = NotificationStatus.QUEUED
    notification.next_attempt_at = None
    notification.failure_code = None
    db.add(
        OutboxEvent(
            tenant_id=notification.tenant_id,
            aggregate_type="notification",
            aggregate_id=notification.id,
            event_type="notification.dlq_replayed",
            payload={"notification_id": notification.id},
        )
    )
    audit(
        db,
        principal,
        "notification.dlq_replayed",
        "notification",
        notification.id,
        request.state.request_id,
        tenant_id=notification.tenant_id,
    )
    db.commit()
    return notification
