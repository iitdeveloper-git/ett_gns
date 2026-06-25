from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ett_gns_app.api import fail
from ett_gns_app.database import get_db
from ett_gns_app.models import (
    DeliveryAttempt,
    DeliveryEvent,
    Notification,
    NotificationStatus,
    ProviderConfig,
)
from ett_gns_app.secrets import SecretStore
from ett_gns_app.settings import Settings, get_settings

router = APIRouter(prefix="/api/v1/callbacks", tags=["callbacks"])

NORMALIZED_STATUSES = {
    "accepted": "provider_accepted",
    "provider_accepted": "provider_accepted",
    "queued": "provider_accepted",
    "sent": "sent",
    "delivered": "delivered",
    "deferred": "deferred",
    "undelivered": "failed",
    "bounced": "bounced",
    "bounce": "bounced",
    "complained": "complained",
    "complaint": "complained",
    "failed": "failed",
    "opened": "opened",
    "open": "opened",
    "clicked": "clicked",
    "click": "clicked",
}


def callback_secrets(provider: ProviderConfig, settings: Settings) -> list[str]:
    secret = SecretStore(settings).decrypt(provider.secret_ciphertext)
    values = (
        secret.get("callback_secrets")
        or secret.get("signing_secrets")
        or [
            secret.get("callback_secret")
            or secret.get("app_secret")
            or secret.get("signing_secret")
        ]
    )
    result = [str(value) for value in values if value]
    if not result:
        fail(409, "callback_secret_missing", "Provider has no callback verification secret")
    return result


def verify_signature(body: bytes, timestamp: str, signature: str, secrets: list[str]) -> None:
    try:
        timestamp_value = int(timestamp)
    except ValueError:
        fail(401, "callback_timestamp_invalid", "Callback timestamp is invalid")
    if abs(int(time.time()) - timestamp_value) > get_settings().callback_replay_window_seconds:
        fail(401, "callback_replay_window", "Callback timestamp is outside replay window")
    supplied = signature.removeprefix("v1=")
    valid = any(
        hmac.compare_digest(
            hmac.new(
                secret.encode(),
                timestamp.encode() + b"." + body,
                hashlib.sha256,
            ).hexdigest(),
            supplied,
        )
        for secret in secrets
    )
    if not valid:
        fail(401, "callback_signature_invalid", "Callback signature is invalid")


def normalize_payload(provider_type: str, payload: dict[str, Any]) -> tuple[str, str, str]:
    provider_event_id = str(
        payload.get("event_id")
        or payload.get("id")
        or payload.get("MessageSid")
        or payload.get("event", {}).get("id")
        or ""
    )
    provider_message_id = str(
        payload.get("message_id")
        or payload.get("MessageSid")
        or payload.get("provider_message_id")
        or payload.get("event", {}).get("message_id")
        or ""
    )
    raw_status = str(
        payload.get("status")
        or payload.get("MessageStatus")
        or payload.get("event", {}).get("type")
        or ""
    ).lower()
    status = NORMALIZED_STATUSES.get(raw_status)
    if not provider_event_id or not provider_message_id or not status:
        fail(422, "callback_payload_invalid", "Callback identity, message ID, or status is missing")
    if status in {"opened", "clicked"} and provider_type not in {
        "sendgrid",
        "mailgun",
        "postmark",
        "fake",
    }:
        fail(
            422,
            "callback_status_unsupported",
            "Provider does not supply supported open/click tracking",
        )
    return provider_event_id, provider_message_id, status


def apply_transition(notification: Notification, event_status: str) -> None:
    if event_status in {"provider_accepted", "sent"}:
        if notification.status not in {
            NotificationStatus.DELIVERED,
            NotificationStatus.FAILED,
            NotificationStatus.CANCELLED,
            NotificationStatus.DEAD_LETTERED,
        }:
            notification.status = NotificationStatus.SENT
    elif event_status == "delivered":
        if notification.status not in {
            NotificationStatus.CANCELLED,
            NotificationStatus.DEAD_LETTERED,
        }:
            notification.status = NotificationStatus.DELIVERED
    elif event_status == "deferred":
        if notification.status not in {
            NotificationStatus.DELIVERED,
            NotificationStatus.CANCELLED,
        }:
            notification.status = NotificationStatus.DEFERRED
    elif event_status in {"failed", "bounced", "complained"}:
        if notification.status != NotificationStatus.CANCELLED:
            notification.status = NotificationStatus.FAILED
            notification.failure_code = event_status.upper()
    # opened/clicked are engagement events and do not regress delivery state.


@router.post("/{provider_id}", status_code=202)
async def process_callback(
    provider_id: str,
    request: Request,
    x_gns_callback_timestamp: str = Header(alias="X-GNS-Callback-Timestamp"),
    x_gns_callback_signature: str = Header(alias="X-GNS-Callback-Signature"),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    provider = db.get(ProviderConfig, provider_id)
    if not provider:
        fail(404, "provider_not_found", "Provider not found")
    body = await request.body()
    if len(body) > settings.max_request_bytes:
        fail(413, "payload_too_large", "Callback payload exceeds configured limit")
    verify_signature(
        body,
        x_gns_callback_timestamp,
        x_gns_callback_signature,
        callback_secrets(provider, settings),
    )
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        fail(422, "callback_json_invalid", "Callback payload must be JSON")
    provider_event_id, provider_message_id, normalized_status = normalize_payload(
        provider.provider_type, payload
    )
    existing = db.scalar(
        select(DeliveryEvent).where(
            DeliveryEvent.provider_config_id == provider.id,
            DeliveryEvent.provider_event_id == provider_event_id,
        )
    )
    if existing:
        return {
            "accepted": True,
            "duplicate": True,
            "delivery_event_id": existing.id,
        }
    attempt = db.scalar(
        select(DeliveryAttempt)
        .where(
            DeliveryAttempt.provider_config_id == provider.id,
            DeliveryAttempt.provider_message_id == provider_message_id,
        )
        .order_by(DeliveryAttempt.created_at.desc())
    )
    if not attempt:
        fail(404, "delivery_attempt_not_found", "Provider message ID is unknown")
    notification = db.get(Notification, attempt.notification_id)
    if not notification:
        fail(404, "notification_not_found", "Notification is unavailable")
    now = datetime.now(UTC)
    delivery_event = DeliveryEvent(
        tenant_id=notification.tenant_id,
        notification_id=notification.id,
        provider_config_id=provider.id,
        provider_event_id=provider_event_id,
        status=normalized_status,
        occurred_at=now,
        raw_payload=payload if settings.callback_raw_retention_days else None,
        raw_payload_expires_at=(
            now + timedelta(days=settings.callback_raw_retention_days)
            if settings.callback_raw_retention_days
            else None
        ),
    )
    db.add(delivery_event)
    apply_transition(notification, normalized_status)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        duplicate = db.scalar(
            select(DeliveryEvent).where(
                DeliveryEvent.provider_config_id == provider.id,
                DeliveryEvent.provider_event_id == provider_event_id,
            )
        )
        if duplicate:
            return {
                "accepted": True,
                "duplicate": True,
                "delivery_event_id": duplicate.id,
            }
        raise
    return {
        "accepted": True,
        "duplicate": False,
        "delivery_event_id": delivery_event.id,
        "status": normalized_status,
    }
