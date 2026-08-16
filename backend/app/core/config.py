from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    app_name: str = "Upcode Harbor"
    app_env: str = "development"
    app_secret_key: str = "development-only-change-me"
    public_app_url: str = "http://localhost:3000"
    backend_cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )
    database_url: str = "sqlite:////data/harbor.db"
    installation_config_path: Path = Path("/data/installation.json")
    access_token_minutes: int = 30
    refresh_token_days: int = 14
    cookie_secure: bool = False
    login_rate_limit: str = "5/minute"

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    def validate_for_startup(self) -> None:
        if self.is_production and self.app_secret_key == "development-only-change-me":
            raise RuntimeError("APP_SECRET_KEY must be changed in production")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
