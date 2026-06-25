from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel):
    items: list[Any]
    total: int
    limit: int
    offset: int


class TenantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,118}[a-z0-9]$")


class TenantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)


class TenantRead(ORMModel):
    id: str
    name: str
    slug: str
    status: str
    created_at: datetime
    updated_at: datetime


class ApplicationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,118}[a-z0-9]$")
    default_locale: str = Field(default="en", max_length=24)
    timezone: str = Field(default="UTC", max_length=64)
    branding: dict[str, Any] = Field(default_factory=dict)
    quota_per_minute: int = Field(default=60, ge=1, le=1_000_000)
    quota_per_day: int = Field(default=10_000, ge=1, le=100_000_000)


class ApplicationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    default_locale: str | None = Field(default=None, max_length=24)
    timezone: str | None = Field(default=None, max_length=64)
    branding: dict[str, Any] | None = None
    quota_per_minute: int | None = Field(default=None, ge=1, le=1_000_000)
    quota_per_day: int | None = Field(default=None, ge=1, le=100_000_000)


class ApplicationRead(ORMModel):
    id: str
    tenant_id: str
    name: str
    slug: str
    status: str
    default_locale: str
    timezone: str
    branding: dict[str, Any]
    quota_per_minute: int
    quota_per_day: int
    created_at: datetime
    updated_at: datetime


class CredentialCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    permissions: list[str] = Field(default_factory=lambda: ["notifications:send"])
    expires_at: datetime | None = None


class CredentialRead(ORMModel):
    id: str
    application_id: str
    name: str
    key_prefix: str
    permissions: list[str]
    expires_at: datetime | None
    last_used_at: datetime | None
    revoked_at: datetime | None
    overlap_ends_at: datetime | None
    created_at: datetime


class CredentialSecret(CredentialRead):
    secret: str


class RotateCredential(BaseModel):
    overlap_seconds: int = Field(default=3600, ge=0, le=604800)


class EventCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event_key: str = Field(pattern=r"^[a-z][a-z0-9_.-]{2,159}$")
    allowed_channels: list[Literal["email", "sms", "webhook", "push", "telegram", "whatsapp"]] = (
        Field(min_length=1)
    )
    recipient_policy: dict[str, Any] = Field(default_factory=dict)
    json_schema: dict[str, Any] = Field(alias="schema")
    compatibility: Literal["none", "backward", "forward", "full"] = "backward"


class EventUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    allowed_channels: list[str] | None = None
    recipient_policy: dict[str, Any] | None = None
    json_schema: dict[str, Any] | None = Field(default=None, alias="schema")
    compatibility: Literal["none", "backward", "forward", "full"] = "backward"


class EventRead(ORMModel):
    id: str
    application_id: str
    event_key: str
    status: str
    allowed_channels: list[str]
    recipient_policy: dict[str, Any]
    current_schema_version: int
    created_at: datetime
    updated_at: datetime


class SchemaVersionRead(ORMModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    event_id: str
    version: int
    json_schema: dict[str, Any] = Field(alias="schema")
    compatibility: str
    created_at: datetime


class NotificationCreate(BaseModel):
    app_id: str
    event_key: str
    channel: Literal["email", "sms", "webhook", "push", "telegram", "whatsapp"]
    recipient: dict[str, Any]
    data: dict[str, Any]
    locale: str | None = None
    variant: str | None = None
    priority: int = Field(default=5, ge=0, le=9)
    scheduled_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NotificationRead(ORMModel):
    id: str
    application_id: str
    event_key: str
    channel: str
    recipient: dict[str, Any]
    event_data: dict[str, Any]
    metadata_json: dict[str, Any]
    locale: str | None
    variant: str | None
    priority: int
    correlation_id: str | None
    status: str
    scheduled_at: datetime | None
    next_attempt_at: datetime | None
    failure_code: str | None
    created_at: datetime
    updated_at: datetime


class EmailRecipient(BaseModel):
    email: EmailStr


class TemplateCreate(BaseModel):
    channel: Literal["email", "sms", "webhook", "push", "telegram", "whatsapp"]
    locale: str = Field(default="en", min_length=2, max_length=24)
    variant: str = Field(default="default", min_length=1, max_length=64)
    content: dict[str, Any]
    sample_data: dict[str, Any] = Field(default_factory=dict)


class TemplateUpdate(BaseModel):
    content: dict[str, Any] | None = None
    sample_data: dict[str, Any] | None = None


class TemplateRead(ORMModel):
    id: str
    application_id: str
    event_id: str
    channel: str
    locale: str
    variant: str
    status: str
    published_version: int | None
    created_at: datetime
    updated_at: datetime


class TemplateVersionRead(ORMModel):
    id: str
    template_id: str
    version: int
    state: str
    content: dict[str, Any]
    sample_data: dict[str, Any]
    validation_errors: list[str]
    published_at: datetime | None
    published_by: str | None
    created_at: datetime
    updated_at: datetime


class TemplatePreview(BaseModel):
    data: dict[str, Any] | None = None


class TemplateTestSend(BaseModel):
    recipient: dict[str, Any]
    data: dict[str, Any] | None = None


class RenderedPreview(BaseModel):
    rendered: dict[str, str]
    locale: str
    variant: str
    version: int


class ProviderCreate(BaseModel):
    channel: Literal["email", "sms", "webhook", "push", "telegram", "whatsapp"]
    provider_type: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    public_config: dict[str, Any] = Field(default_factory=dict)
    secret: dict[str, Any] | None = None
    is_default: bool = False
    fallback_policy: Literal["none", "default_if_absent", "explicit_failover"] = "none"
    fallback_provider_id: str | None = None


class ProviderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    public_config: dict[str, Any] | None = None
    is_default: bool | None = None
    fallback_policy: Literal["none", "default_if_absent", "explicit_failover"] | None = None
    fallback_provider_id: str | None = None


class ProviderRead(ORMModel):
    id: str
    tenant_id: str
    application_id: str | None
    channel: str
    provider_type: str
    name: str
    public_config: dict[str, Any]
    active: bool
    is_default: bool
    fallback_policy: str
    fallback_provider_id: str | None
    health_status: str
    verified_at: datetime | None
    last_error_code: str | None
    created_at: datetime
    updated_at: datetime
    secret_configured: bool = False


class ProviderSecretReplace(BaseModel):
    secret: dict[str, Any]


class ProviderTestResult(BaseModel):
    valid: bool
    health_status: str
    errors: list[str] = Field(default_factory=list)
