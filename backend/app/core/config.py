from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    app_name: str = "Upcode sprint"
    app_version: str = "0.1.0"
    app_env: str = "development"
    app_secret_key: str = "development-only-change-me-32chars"
    public_app_url: str = "http://localhost:3000"
    backend_cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )
    database_url: str = "sqlite:////data/sprint.db"
    installation_config_path: Path = Path("/data/installation.json")
    access_token_minutes: int = 30
    refresh_token_days: int = 14
    cookie_secure: bool = False
    login_rate_limit: str = "5/minute"
    avatar_storage_path: Path = Path("/data/avatars")
    avatar_max_bytes: int = 5 * 1024 * 1024
    organization_logo_storage_path: Path = Path("/data/organization-logos")
    organization_logo_max_bytes: int = 5 * 1024 * 1024
    presence_heartbeat_interval: int = 60
    presence_away_after: int = 300
    presence_offline_after: int = 900

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @model_validator(mode="after")
    def validate_presence_thresholds(self) -> "Settings":
        if self.avatar_max_bytes < 1024:
            raise ValueError("AVATAR_MAX_BYTES must be at least 1024")
        if self.organization_logo_max_bytes < 1024:
            raise ValueError("ORGANIZATION_LOGO_MAX_BYTES must be at least 1024")
        if not 1 <= self.presence_heartbeat_interval <= self.presence_away_after:
            raise ValueError("PRESENCE_HEARTBEAT_INTERVAL must not exceed PRESENCE_AWAY_AFTER")
        if self.presence_away_after >= self.presence_offline_after:
            raise ValueError("PRESENCE_OFFLINE_AFTER must be greater than PRESENCE_AWAY_AFTER")
        return self

    def validate_for_startup(self) -> None:
        insecure = (
            len(self.app_secret_key) < 32
            or self.app_secret_key.startswith("development-only-change-me")
            or self.app_secret_key.upper().startswith("CHANGE_ME")
        )
        if self.is_production and insecure:
            raise RuntimeError("APP_SECRET_KEY must be a strong secret in production")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
