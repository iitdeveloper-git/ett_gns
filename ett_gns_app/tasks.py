from __future__ import annotations

from datetime import UTC, datetime, timedelta

from celery import Celery
from sqlalchemy import select

from ett_gns_app.database import SessionLocal
from ett_gns_app.delivery import process_notification, reconcile_stuck_notifications
from ett_gns_app.models import Notification, NotificationStatus, OutboxEvent
from ett_gns_app.settings import get_settings

settings = get_settings()
celery_app = Celery(
    "gns",
    broker=settings.broker_url,
    backend=settings.result_backend_url,
)
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    task_routes={
        "gns.deliver": {"queue": "notifications.default"},
        "gns.publish_outbox": {"queue": "outbox"},
        "gns.reconcile": {"queue": "maintenance"},
    },
    beat_schedule={
        "publish-outbox": {"task": "gns.publish_outbox", "schedule": 2.0},
        "reconcile": {"task": "gns.reconcile", "schedule": 30.0},
    },
)


@celery_app.task(name="gns.deliver")
def deliver(notification_id: str) -> str:
    with SessionLocal() as db:
        return process_notification(db, notification_id, settings).status


@celery_app.task(name="gns.publish_outbox")
def publish_outbox(batch_size: int = 100) -> int:
    now = datetime.now(UTC)
    published = 0
    with SessionLocal() as db:
        rows = list(
            db.scalars(
                select(OutboxEvent)
                .where(
                    OutboxEvent.published_at.is_(None),
                    (OutboxEvent.lease_until.is_(None)) | (OutboxEvent.lease_until < now),
                )
                .order_by(OutboxEvent.created_at)
                .limit(batch_size)
            )
        )
        for row in rows:
            available_at = row.payload.get("available_at")
            eta = datetime.fromisoformat(available_at) if available_at else None
            if eta and eta.tzinfo is None:
                eta = eta.replace(tzinfo=UTC)
            row.lease_until = now + timedelta(seconds=30)
            row.publish_attempts += 1
            db.commit()
            try:
                deliver.apply_async(args=[row.aggregate_id], eta=eta)
                row.published_at = datetime.now(UTC)
                row.last_error = None
                notification = db.get(Notification, row.aggregate_id)
                if notification and notification.status in {
                    NotificationStatus.ACCEPTED,
                    NotificationStatus.DEFERRED,
                }:
                    notification.status = NotificationStatus.QUEUED
                published += 1
            except Exception as exc:
                row.last_error = str(exc)[:2000]
            finally:
                row.lease_until = None
                db.commit()
    return published


@celery_app.task(name="gns.reconcile")
def reconcile() -> dict[str, int]:
    with SessionLocal() as db:
        return {"stuck_notifications": reconcile_stuck_notifications(db, settings)}
