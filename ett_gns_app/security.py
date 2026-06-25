from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ett_gns_app.database import get_db
from ett_gns_app.models import ApplicationCredential
from ett_gns_app.settings import Settings, get_settings

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "platform_admin": {"*"},
    "tenant_admin": {
        "apps:read",
        "apps:write",
        "credentials:rotate",
        "events:manage",
        "templates:write",
        "templates:publish",
        "providers:manage",
        "notifications:read",
        "notifications:retry",
        "audit:read",
    },
    "application_admin": {
        "apps:read",
        "apps:write",
        "credentials:rotate",
        "events:manage",
        "templates:write",
        "providers:manage",
        "notifications:read",
    },
    "template_editor": {"apps:read", "events:manage", "templates:write"},
    "template_publisher": {"apps:read", "templates:write", "templates:publish"},
    "operations_viewer": {"apps:read", "notifications:read"},
    "operations_operator": {
        "apps:read",
        "notifications:read",
        "notifications:retry",
    },
    "auditor": {"apps:read", "notifications:read", "audit:read"},
}


@dataclass(frozen=True)
class Principal:
    subject: str
    tenant_id: str | None
    roles: frozenset[str]
    permissions: frozenset[str]
    actor_type: str = "human"
    application_id: str | None = None
    credential_id: str | None = None

    def can(self, permission: str) -> bool:
        return "*" in self.permissions or permission in self.permissions


def _derive_hash(secret: str, salt: bytes, pepper: str) -> bytes:
    return hashlib.scrypt(
        secret.encode(),
        salt=salt + pepper.encode(),
        n=2**14,
        r=8,
        p=1,
        dklen=32,
    )


def generate_api_key(settings: Settings) -> tuple[str, str, bytes, bytes]:
    key_prefix = secrets.token_urlsafe(9).replace("-", "").replace("_", "")[:12]
    secret = secrets.token_urlsafe(32)
    salt = os.urandom(16)
    digest = _derive_hash(secret, salt, settings.api_key_pepper)
    return f"gns_{key_prefix}.{secret}", key_prefix, salt, digest


def verify_api_key(secret: str, salt: bytes, expected: bytes, settings: Settings) -> bool:
    return hmac.compare_digest(_derive_hash(secret, salt, settings.api_key_pepper), expected)


def permissions_for_roles(roles: set[str]) -> frozenset[str]:
    permissions: set[str] = set()
    for role in roles:
        permissions.update(ROLE_PERMISSIONS.get(role, set()))
    return frozenset(permissions)


def get_admin_principal(
    request: Request,
    settings: Settings = Depends(get_settings),
    x_admin_user: str | None = Header(default=None),
    x_admin_roles: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None),
) -> Principal:
    if settings.allow_dev_identity and settings.environment in {"development", "test"}:
        if not x_admin_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "identity_required",
                    "message": "Development identity header missing",
                },
            )
        roles = {role.strip() for role in (x_admin_roles or "").split(",") if role.strip()}
        unknown = roles - ROLE_PERMISSIONS.keys()
        if not roles or unknown:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "invalid_roles",
                    "message": "No valid administrative role supplied",
                },
            )
        return Principal(
            subject=x_admin_user,
            tenant_id=x_tenant_id,
            roles=frozenset(roles),
            permissions=permissions_for_roles(roles),
        )
    authorization = request.headers.get("authorization", "")
    if not settings.oidc_issuer or not settings.oidc_audience:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={"code": "oidc_not_configured", "message": "OIDC verifier is not configured"},
        )
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "identity_required", "message": "OIDC bearer token required"},
        )
    token = authorization.removeprefix("Bearer ")
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
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "oidc_token_invalid", "message": "OIDC token validation failed"},
        ) from exc
    roles_claim = claims.get("roles") or claims.get("realm_access", {}).get("roles", [])
    roles = {str(role) for role in roles_claim if str(role) in ROLE_PERMISSIONS}
    if not roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "roles_missing", "message": "Token has no recognized GNS roles"},
        )
    return Principal(
        subject=str(claims["sub"]),
        tenant_id=claims.get("tenant_id"),
        roles=frozenset(roles),
        permissions=permissions_for_roles(roles),
    )


def require(permission: str) -> Callable[..., Principal]:
    def dependency(principal: Principal = Depends(get_admin_principal)) -> Principal:
        if not principal.can(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "permission_denied", "message": f"Requires {permission}"},
            )
        return principal

    return dependency


def get_app_principal(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Principal:
    authorization = request.headers.get("authorization", "")
    if not authorization.startswith("Bearer gns_") or "." not in authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "invalid_credential",
                "message": "Valid application bearer key required",
            },
        )
    token = authorization.removeprefix("Bearer ")
    prefix_part, secret = token.split(".", 1)
    key_prefix = prefix_part.removeprefix("gns_")
    credential = db.scalar(
        select(ApplicationCredential).where(ApplicationCredential.key_prefix == key_prefix)
    )
    now = datetime.now(UTC)
    overlap_expired = (
        credential is not None
        and credential.replaced_by_id is not None
        and credential.overlap_ends_at is not None
        and credential.overlap_ends_at.replace(tzinfo=credential.overlap_ends_at.tzinfo or UTC)
        <= now
    )
    expires_at = (
        credential.expires_at.replace(tzinfo=credential.expires_at.tzinfo or UTC)
        if credential is not None and credential.expires_at is not None
        else None
    )
    invalid = (
        credential is None
        or credential.revoked_at is not None
        or overlap_expired
        or (expires_at is not None and expires_at <= now)
    )
    if (
        invalid
        or credential is None
        or not verify_api_key(secret, credential.secret_salt, credential.secret_hash, settings)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_credential", "message": "Credential is invalid or expired"},
        )
    credential.last_used_at = now
    db.commit()
    return Principal(
        subject=credential.id,
        tenant_id=credential.tenant_id,
        roles=frozenset(),
        permissions=frozenset(credential.permissions),
        actor_type="application",
        application_id=credential.application_id,
        credential_id=credential.id,
    )
