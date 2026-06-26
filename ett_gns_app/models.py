from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ett_gns_app.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class Lifecycle(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    ARCHIVED = "archived"


class TemplateState(StrEnum):
    DRAFT = "draft"
    VALIDATED = "validated"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class NotificationStatus(StrEnum):
    ACCEPTED = "accepted"
    QUEUED = "queued"
    PROCESSING = "processing"
    SENT = "sent"
    DELIVERED = "delivered"
    DEFERRED = "deferred"
    FAILED = "failed"
    DEAD_LETTERED = "dead_lettered"
    CANCELLED = "cancelled"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Tenant(TimestampMixin, Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("tnt"))
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(24), default=Lifecycle.ACTIVE)

    applications: Mapped[list[Application]] = relationship(back_populates="tenant")


class Application(TimestampMixin, Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("tenant_id", "slug"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("app"))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(24), default=Lifecycle.ACTIVE)
    default_locale: Mapped[str] = mapped_column(String(24), default="en")
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    branding: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    quota_per_minute: Mapped[int] = mapped_column(Integer, default=60)
    quota_per_day: Mapped[int] = mapped_column(Integer, default=10000)

    tenant: Mapped[Tenant] = relationship(back_populates="applications")
    credentials: Mapped[list[ApplicationCredential]] = relationship(back_populates="application")
    events: Mapped[list[Event]] = relationship(back_populates="application")


class ApplicationCredential(TimestampMixin, Base):
    __tablename__ = "application_credentials"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("key"))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    key_prefix: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    secret_salt: Mapped[bytes] = mapped_column(LargeBinary)
    secret_hash: Mapped[bytes] = mapped_column(LargeBinary)
    permissions: Mapped[list[str]] = mapped_column(JSON, default=list)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    overlap_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by_id: Mapped[str | None] = mapped_column(
        ForeignKey("application_credentials.id"), nullable=True
    )

    application: Mapped[Application] = relationship(back_populates="credentials")


class Event(TimestampMixin, Base):
    __tablename__ = "events"
    __table_args__ = (UniqueConstraint("application_id", "event_key"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("evt"))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id"), index=True)
    event_key: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(24), default=Lifecycle.ACTIVE)
    allowed_channels: Mapped[list[str]] = mapped_column(JSON, default=list)
    recipient_policy: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    current_schema_version: Mapped[int] = mapped_column(Integer, default=1)

    application: Mapped[Application] = relationship(back_populates="events")
    schema_versions: Mapped[list[EventSchemaVersion]] = relationship(back_populates="event")


class EventSchemaVersion(TimestampMixin, Base):
    __tablename__ = "event_schema_versions"
    __table_args__ = (UniqueConstraint("event_id", "version"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("sch"))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    schema: Mapped[dict[str, Any]] = mapped_column(JSON)
    compatibility: Mapped[str] = mapped_column(String(32), default="backward")

    event: Mapped[Event] = relationship(back_populates="schema_versions")


class Template(TimestampMixin, Base):
    __tablename__ = "templates"
    __table_args__ = (
        UniqueConstraint("application_id", "event_id", "channel", "locale", "variant"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("tpl"))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id"), index=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), index=True)
    channel: Mapped[str] = mapped_column(String(32))
    locale: Mapped[str] = mapped_column(String(24))
    variant: Mapped[str] = mapped_column(String(64), default="default")
    status: Mapped[str] = mapped_column(String(24), default=Lifecycle.ACTIVE)
    published_version: Mapped[int | None] = mapped_column(Integer)


class TemplateVersion(TimestampMixin, Base):
    __tablename__ = "template_versions"
    __table_args__ = (UniqueConstraint("template_id", "version"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("tpv"))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    template_id: Mapped[str] = mapped_column(ForeignKey("templates.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(24), default=TemplateState.DRAFT)
    content: Mapped[dict[str, Any]] = mapped_column(JSON)
    sample_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    validation_errors: Mapped[list[str]] = mapped_column(JSON, default=list)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_by: Mapped[str | None] = mapped_column(String(200))


class ProviderConfig(TimestampMixin, Base):
    __tablename__ = "provider_configs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("prv"))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    application_id: Mapped[str | None] = mapped_column(
        ForeignKey("applications.id"), nullable=True, index=True
    )
    channel: Mapped[str] = mapped_column(String(32), index=True)
    provider_type: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(120))
    public_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    secret_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    secret_key_id: Mapped[str | None] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    fallback_policy: Mapped[str] = mapped_column(String(32), default="none")
    fallback_provider_id: Mapped[str | None] = mapped_column(
        ForeignKey("provider_configs.id"), nullable=True
    )
    health_status: Mapped[str] = mapped_column(String(32), default="unknown")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(120))


class Notification(TimestampMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("application_id", "idempotency_key"),
        Index("ix_notifications_status_scheduled", "status", "scheduled_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("ntf"))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id"), index=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), index=True)
    event_key: Mapped[str] = mapped_column(String(160))
    channel: Mapped[str] = mapped_column(String(32))
    recipient: Mapped[dict[str, Any]] = mapped_column(JSON)
    event_data: Mapped[dict[str, Any]] = mapped_column(JSON)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    locale: Mapped[str | None] = mapped_column(String(24))
    variant: Mapped[str | None] = mapped_column(String(64))
    priority: Mapped[int] = mapped_column(Integer, default=5)
    correlation_id: Mapped[str | None] = mapped_column(String(120), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(200))
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default=NotificationStatus.ACCEPTED)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    template_version_id: Mapped[str | None] = mapped_column(ForeignKey("template_versions.id"))
    provider_config_id: Mapped[str | None] = mapped_column(ForeignKey("provider_configs.id"))
    processing_lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_code: Mapped[str | None] = mapped_column(String(120))


class DeliveryAttempt(TimestampMixin, Base):
    __tablename__ = "delivery_attempts"
    __table_args__ = (UniqueConstraint("notification_id", "attempt_number"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("atm"))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    notification_id: Mapped[str] = mapped_column(ForeignKey("notifications.id"), index=True)
    attempt_number: Mapped[int] = mapped_column(Integer)
    provider_config_id: Mapped[str | None] = mapped_column(ForeignKey("provider_configs.id"))
    status: Mapped[str] = mapped_column(String(32))
    retryable: Mapped[bool] = mapped_column(Boolean, default=False)
    error_code: Mapped[str | None] = mapped_column(String(120))
    error_message: Mapped[str | None] = mapped_column(Text)
    provider_message_id: Mapped[str | None] = mapped_column(String(240), index=True)
    response_excerpt: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)


class DeliveryEvent(TimestampMixin, Base):
    __tablename__ = "delivery_events"
    __table_args__ = (UniqueConstraint("provider_config_id", "provider_event_id"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("dve"))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    notification_id: Mapped[str] = mapped_column(ForeignKey("notifications.id"), index=True)
    provider_config_id: Mapped[str] = mapped_column(ForeignKey("provider_configs.id"))
    provider_event_id: Mapped[str] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(String(32))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    raw_payload_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OutboxEvent(TimestampMixin, Base):
    __tablename__ = "outbox_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("obx"))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    aggregate_type: Mapped[str] = mapped_column(String(64))
    aggregate_id: Mapped[str] = mapped_column(String(64), index=True)
    event_type: Mapped[str] = mapped_column(String(120))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    publish_attempts: Mapped[int] = mapped_column(Integer, default=0)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("aud"))
    tenant_id: Mapped[str | None] = mapped_column(
        ForeignKey("tenants.id"), nullable=True, index=True
    )
    actor_id: Mapped[str] = mapped_column(String(200))
    actor_type: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(160), index=True)
    target_type: Mapped[str] = mapped_column(String(80))
    target_id: Mapped[str] = mapped_column(String(80))
    request_id: Mapped[str | None] = mapped_column(String(120), index=True)
    changes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UsageBucket(Base):
    __tablename__ = "usage_buckets"
    __table_args__ = (UniqueConstraint("application_id", "bucket_kind", "bucket_start"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("use"))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id"), index=True)
    channel: Mapped[str] = mapped_column(String(32))
    bucket_kind: Mapped[str] = mapped_column(String(16))
    bucket_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    count: Mapped[int] = mapped_column(Integer, default=0)


class InAppNotification(TimestampMixin, Base):
    __tablename__ = "in_app_notifications"
    __table_args__ = (
        UniqueConstraint("tenant_id", "application_id", "deduplication_key"),
        Index("ix_in_app_notifications_active", "tenant_id", "application_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("ian"))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id"), index=True)
    source_notification_id: Mapped[str] = mapped_column(ForeignKey("notifications.id"), index=True)
    event_key: Mapped[str] = mapped_column(String(160), index=True)
    template_version_id: Mapped[str | None] = mapped_column(ForeignKey("template_versions.id"))
    title: Mapped[str] = mapped_column(String(240))
    message: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(24), default="info")
    priority: Mapped[int] = mapped_column(Integer, default=5)
    action_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    toast_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deduplication_key: Mapped[str | None] = mapped_column(String(240))
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    correlation_id: Mapped[str | None] = mapped_column(String(120), index=True)


class InAppRecipient(TimestampMixin, Base):
    __tablename__ = "in_app_recipients"
    __table_args__ = (
        UniqueConstraint("notification_id", "recipient_type", "recipient_id"),
        Index("ix_in_app_recipients_inbox", "tenant_id", "application_id", "recipient_id", "read_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("iar"))
    notification_id: Mapped[str] = mapped_column(ForeignKey("in_app_notifications.id"), index=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id"), index=True)
    recipient_type: Mapped[str] = mapped_column(String(32))
    recipient_id: Mapped[str] = mapped_column(String(200), index=True)
    delivery_status: Mapped[str] = mapped_column(String(32), default="created")
    delivery_attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    displayed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InAppDeliveryAttempt(Base):
    __tablename__ = "in_app_delivery_attempts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("iad"))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    notification_recipient_id: Mapped[str] = mapped_column(
        ForeignKey("in_app_recipients.id"), index=True
    )
    attempt_number: Mapped[int] = mapped_column(Integer)
    transport: Mapped[str] = mapped_column(String(32), default="sse")
    status: Mapped[str] = mapped_column(String(32))
    error_code: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InAppConnection(Base):
    __tablename__ = "in_app_connections"

    connection_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(200), index=True)
    session_id: Mapped[str] = mapped_column(String(200), index=True)
    transport: Mapped[str] = mapped_column(String(32), default="sse")
    device_id: Mapped[str | None] = mapped_column(String(200))
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class InAppPreference(TimestampMixin, Base):
    __tablename__ = "in_app_preferences"
    __table_args__ = (UniqueConstraint("tenant_id", "application_id", "user_id", "event_key"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("iap"))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(200), index=True)
    event_key: Mapped[str] = mapped_column(String(160), default="*")
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    toast_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sound_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    quiet_hours: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    minimum_priority: Mapped[int] = mapped_column(Integer, default=1)
