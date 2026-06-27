"""add in-app notifications

Revision ID: 4a0f8c9d2b11
Revises: 2ba920e67437
Create Date: 2026-06-26 21:34:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4a0f8c9d2b11"
down_revision: Union[str, Sequence[str], None] = "2ba920e67437"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "in_app_notifications",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("application_id", sa.String(length=64), nullable=False),
        sa.Column("source_notification_id", sa.String(length=64), nullable=False),
        sa.Column("event_key", sa.String(length=160), nullable=False),
        sa.Column("template_version_id", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=24), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("action_payload", sa.JSON(), nullable=False),
        sa.Column("toast_payload", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deduplication_key", sa.String(length=240), nullable=True),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("correlation_id", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
        sa.ForeignKeyConstraint(["source_notification_id"], ["notifications.id"]),
        sa.ForeignKeyConstraint(["template_version_id"], ["template_versions.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "application_id", "deduplication_key"),
    )
    op.create_index(
        "ix_in_app_notifications_active",
        "in_app_notifications",
        ["tenant_id", "application_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_in_app_notifications_application_id"),
        "in_app_notifications",
        ["application_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_in_app_notifications_correlation_id"),
        "in_app_notifications",
        ["correlation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_in_app_notifications_event_key"),
        "in_app_notifications",
        ["event_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_in_app_notifications_expires_at"),
        "in_app_notifications",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_in_app_notifications_source_notification_id"),
        "in_app_notifications",
        ["source_notification_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_in_app_notifications_tenant_id"),
        "in_app_notifications",
        ["tenant_id"],
        unique=False,
    )
    op.create_table(
        "in_app_recipients",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("notification_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("application_id", sa.String(length=64), nullable=False),
        sa.Column("recipient_type", sa.String(length=32), nullable=False),
        sa.Column("recipient_id", sa.String(length=200), nullable=False),
        sa.Column("delivery_status", sa.String(length=32), nullable=False),
        sa.Column("delivery_attempt_count", sa.Integer(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("displayed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
        sa.ForeignKeyConstraint(["notification_id"], ["in_app_notifications.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("notification_id", "recipient_type", "recipient_id"),
    )
    op.create_index(
        "ix_in_app_recipients_inbox",
        "in_app_recipients",
        ["tenant_id", "application_id", "recipient_id", "read_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_in_app_recipients_application_id"),
        "in_app_recipients",
        ["application_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_in_app_recipients_notification_id"),
        "in_app_recipients",
        ["notification_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_in_app_recipients_read_at"),
        "in_app_recipients",
        ["read_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_in_app_recipients_recipient_id"),
        "in_app_recipients",
        ["recipient_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_in_app_recipients_tenant_id"),
        "in_app_recipients",
        ["tenant_id"],
        unique=False,
    )
    op.create_table(
        "in_app_delivery_attempts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("notification_recipient_id", sa.String(length=64), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("transport", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_code", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["notification_recipient_id"], ["in_app_recipients.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_in_app_delivery_attempts_notification_recipient_id"),
        "in_app_delivery_attempts",
        ["notification_recipient_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_in_app_delivery_attempts_tenant_id"),
        "in_app_delivery_attempts",
        ["tenant_id"],
        unique=False,
    )
    op.create_table(
        "in_app_connections",
        sa.Column("connection_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("application_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=200), nullable=False),
        sa.Column("session_id", sa.String(length=200), nullable=False),
        sa.Column("transport", sa.String(length=32), nullable=False),
        sa.Column("device_id", sa.String(length=200), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("connection_id"),
    )
    op.create_index(
        op.f("ix_in_app_connections_application_id"),
        "in_app_connections",
        ["application_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_in_app_connections_session_id"),
        "in_app_connections",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_in_app_connections_tenant_id"),
        "in_app_connections",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_in_app_connections_user_id"),
        "in_app_connections",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "in_app_preferences",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("application_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=200), nullable=False),
        sa.Column("event_key", sa.String(length=160), nullable=False),
        sa.Column("in_app_enabled", sa.Boolean(), nullable=False),
        sa.Column("toast_enabled", sa.Boolean(), nullable=False),
        sa.Column("sound_enabled", sa.Boolean(), nullable=False),
        sa.Column("quiet_hours", sa.JSON(), nullable=False),
        sa.Column("minimum_priority", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "application_id", "user_id", "event_key"),
    )
    op.create_index(
        op.f("ix_in_app_preferences_application_id"),
        "in_app_preferences",
        ["application_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_in_app_preferences_tenant_id"),
        "in_app_preferences",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_in_app_preferences_user_id"),
        "in_app_preferences",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_in_app_preferences_user_id"), table_name="in_app_preferences")
    op.drop_index(op.f("ix_in_app_preferences_tenant_id"), table_name="in_app_preferences")
    op.drop_index(op.f("ix_in_app_preferences_application_id"), table_name="in_app_preferences")
    op.drop_table("in_app_preferences")
    op.drop_index(op.f("ix_in_app_connections_user_id"), table_name="in_app_connections")
    op.drop_index(op.f("ix_in_app_connections_tenant_id"), table_name="in_app_connections")
    op.drop_index(op.f("ix_in_app_connections_session_id"), table_name="in_app_connections")
    op.drop_index(op.f("ix_in_app_connections_application_id"), table_name="in_app_connections")
    op.drop_table("in_app_connections")
    op.drop_index(
        op.f("ix_in_app_delivery_attempts_tenant_id"), table_name="in_app_delivery_attempts"
    )
    op.drop_index(
        op.f("ix_in_app_delivery_attempts_notification_recipient_id"),
        table_name="in_app_delivery_attempts",
    )
    op.drop_table("in_app_delivery_attempts")
    op.drop_index(op.f("ix_in_app_recipients_tenant_id"), table_name="in_app_recipients")
    op.drop_index(op.f("ix_in_app_recipients_recipient_id"), table_name="in_app_recipients")
    op.drop_index(op.f("ix_in_app_recipients_read_at"), table_name="in_app_recipients")
    op.drop_index(op.f("ix_in_app_recipients_notification_id"), table_name="in_app_recipients")
    op.drop_index(op.f("ix_in_app_recipients_application_id"), table_name="in_app_recipients")
    op.drop_index("ix_in_app_recipients_inbox", table_name="in_app_recipients")
    op.drop_table("in_app_recipients")
    op.drop_index(op.f("ix_in_app_notifications_tenant_id"), table_name="in_app_notifications")
    op.drop_index(
        op.f("ix_in_app_notifications_source_notification_id"),
        table_name="in_app_notifications",
    )
    op.drop_index(op.f("ix_in_app_notifications_expires_at"), table_name="in_app_notifications")
    op.drop_index(op.f("ix_in_app_notifications_event_key"), table_name="in_app_notifications")
    op.drop_index(
        op.f("ix_in_app_notifications_correlation_id"), table_name="in_app_notifications"
    )
    op.drop_index(
        op.f("ix_in_app_notifications_application_id"), table_name="in_app_notifications"
    )
    op.drop_index("ix_in_app_notifications_active", table_name="in_app_notifications")
    op.drop_table("in_app_notifications")
