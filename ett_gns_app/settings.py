from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GNS_",
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    environment: Literal["development", "test", "staging", "production"] = "development"
    database_url: str = "sqlite:///./gns.db"
    broker_url: str = "amqp://guest:guest@localhost:5672//"
    result_backend_url: str = "redis://localhost:6379/0"
    allow_dev_identity: bool = True
    dev_tenant_id: str | None = None
    oidc_issuer: str | None = None
    oidc_audience: str | None = None
    api_key_pepper: str = Field(default="development-only-change-me", min_length=16)
    provider_secret_key: str | None = None
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )
    max_request_bytes: int = Field(default=1_048_576, ge=1024, le=10_485_760)
    platform_default_locale: str = "en"
    callback_replay_window_seconds: int = Field(default=300, ge=30, le=3600)
    callback_raw_retention_days: int = Field(default=30, ge=0, le=365)
    processing_lease_seconds: int = Field(default=120, ge=10, le=3600)
    max_delivery_attempts: int = Field(default=6, ge=1, le=20)

    @model_validator(mode="after")
    def validate_production_safety(self) -> "Settings":
        if self.environment == "production":
            if self.allow_dev_identity:
                raise ValueError("GNS_ALLOW_DEV_IDENTITY must be false in production")
            if self.api_key_pepper == "development-only-change-me":
                raise ValueError("GNS_API_KEY_PEPPER must be changed in production")
            if not self.oidc_issuer or not self.oidc_audience:
                raise ValueError("OIDC issuer and audience are required in production")
            if not self.provider_secret_key:
                raise ValueError("GNS_PROVIDER_SECRET_KEY is required in production")
            if not self.database_url.startswith("postgresql"):
                raise ValueError("Production requires PostgreSQL")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
