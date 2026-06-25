from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ett_gns_app.models import (
    Application,
    Event,
    ProviderConfig,
    Template,
    TemplateState,
    TemplateVersion,
)


class ResolutionError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class ResolvedDelivery:
    template: Template
    template_version: TemplateVersion
    provider: ProviderConfig
    sender: dict[str, Any]


def resolve_template(
    db: Session,
    app: Application,
    event: Event,
    channel: str,
    requested_locale: str | None,
    requested_variant: str | None,
    platform_locale: str,
) -> tuple[Template, TemplateVersion]:
    locales = list(
        dict.fromkeys(
            locale for locale in [requested_locale, app.default_locale, platform_locale] if locale
        )
    )
    variants = list(dict.fromkeys([requested_variant or "default", "default"]))
    for locale in locales:
        for variant in variants:
            template = db.scalar(
                select(Template).where(
                    Template.application_id == app.id,
                    Template.event_id == event.id,
                    Template.channel == channel,
                    Template.locale == locale,
                    Template.variant == variant,
                    Template.status == "active",
                    Template.published_version.is_not(None),
                )
            )
            if not template or template.published_version is None:
                continue
            version = db.scalar(
                select(TemplateVersion).where(
                    TemplateVersion.template_id == template.id,
                    TemplateVersion.version == template.published_version,
                    TemplateVersion.state == TemplateState.PUBLISHED,
                )
            )
            if version:
                return template, version
    raise ResolutionError(
        "template_not_found",
        "No published template matches the requested channel, locale, and variant",
    )


def resolve_provider(db: Session, app: Application, channel: str) -> ProviderConfig:
    app_providers = list(
        db.scalars(
            select(ProviderConfig)
            .where(
                ProviderConfig.application_id == app.id,
                ProviderConfig.channel == channel,
            )
            .order_by(ProviderConfig.created_at.desc())
        )
    )
    if app_providers:
        primary = app_providers[0]
        if primary.active and primary.health_status == "healthy":
            return primary
        authentication_failure = primary.health_status in {
            "authentication_failed",
            "invalid",
        }
        if (
            not authentication_failure
            and primary.fallback_policy == "explicit_failover"
            and primary.fallback_provider_id
        ):
            fallback = db.get(ProviderConfig, primary.fallback_provider_id)
            if (
                fallback
                and fallback.application_id == app.id
                and fallback.channel == channel
                and fallback.active
                and fallback.health_status == "healthy"
            ):
                return fallback
        # Authentication/configuration failure must never silently switch sender or brand.
        raise ResolutionError(
            "app_provider_unavailable",
            "An app-specific provider is configured but no active healthy provider is available",
        )
    default = db.scalar(
        select(ProviderConfig).where(
            ProviderConfig.tenant_id == app.tenant_id,
            ProviderConfig.application_id.is_(None),
            ProviderConfig.channel == channel,
            ProviderConfig.is_default.is_(True),
            ProviderConfig.active.is_(True),
            ProviderConfig.health_status == "healthy",
            ProviderConfig.fallback_policy == "default_if_absent",
        )
    )
    if default:
        return default
    raise ResolutionError(
        "provider_not_found",
        "No app provider exists and no policy-approved default provider is available",
    )


def resolve_email_sender(app: Application, provider: ProviderConfig) -> dict[str, Any]:
    config = provider.public_config
    authenticated_sender = config.get("from_email")
    if not authenticated_sender:
        raise ResolutionError("sender_invalid", "Email provider has no authenticated sender")
    sender: dict[str, Any] = {"from_email": authenticated_sender}
    configured_name = config.get("from_name")
    app_name = app.branding.get("display_name") if app.branding else None
    if provider.application_id is not None and provider.application_id == app.id:
        sender["from_name"] = configured_name or app_name or app.name
    elif config.get("allow_app_display_name", False):
        sender["from_name"] = app_name or app.name
    else:
        sender["from_name"] = configured_name
    requested_reply_to = app.branding.get("reply_to") if app.branding else None
    verified_reply_to = set(config.get("verified_reply_to", []))
    if requested_reply_to and requested_reply_to in verified_reply_to:
        sender["reply_to"] = requested_reply_to
    return {key: value for key, value in sender.items() if value}


def resolve_delivery(
    db: Session,
    app: Application,
    event: Event,
    channel: str,
    requested_locale: str | None,
    requested_variant: str | None,
    platform_locale: str,
) -> ResolvedDelivery:
    template, template_version = resolve_template(
        db,
        app,
        event,
        channel,
        requested_locale,
        requested_variant,
        platform_locale,
    )
    provider = resolve_provider(db, app, channel)
    sender = resolve_email_sender(app, provider) if channel == "email" else {}
    return ResolvedDelivery(
        template=template,
        template_version=template_version,
        provider=provider,
        sender=sender,
    )
