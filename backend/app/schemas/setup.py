from typing import Literal

from pydantic import EmailStr, Field, SecretStr, field_validator, model_validator

from app.schemas.common import APIModel


class DatabaseConfiguration(APIModel):
    engine: Literal["sqlite", "postgresql", "mysql", "mariadb"]
    sqlite_path: str | None = None
    host: str | None = None
    port: int | None = Field(default=None, ge=1, le=65535)
    database: str | None = None
    username: str | None = None
    password: SecretStr | None = None
    ssl: bool = False

    @model_validator(mode="after")
    def validate_engine_fields(self) -> "DatabaseConfiguration":
        if self.engine == "sqlite":
            if not self.sqlite_path:
                raise ValueError("SQLite path is required")
        elif not all([self.host, self.port, self.database, self.username, self.password]):
            raise ValueError("Host, port, database, username and password are required")
        return self


class AdminSetup(APIModel):
    username: str = Field(min_length=3, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: EmailStr
    password: SecretStr
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: SecretStr) -> SecretStr:
        password = value.get_secret_value()
        if len(password) < 12:
            raise ValueError("Password must contain at least 12 characters")
        if not (any(c.islower() for c in password) and any(c.isupper() for c in password)):
            raise ValueError("Password must contain upper- and lowercase characters")
        if not any(c.isdigit() for c in password):
            raise ValueError("Password must contain a number")
        return value


class SMTPSetup(APIModel):
    enabled: bool = False
    host: str | None = None
    port: int | None = Field(default=None, ge=1, le=65535)
    username: str | None = None
    password: SecretStr | None = None
    encryption: Literal["none", "starttls", "tls"] = "none"
    from_address: EmailStr | None = None
    from_name: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def validate_enabled_fields(self) -> "SMTPSetup":
        if self.enabled and not all([self.host, self.port, self.from_address, self.from_name]):
            raise ValueError("SMTP host, port, from address and from name are required")
        return self


class SetupCompleteRequest(APIModel):
    organization_name: str = Field(min_length=2, max_length=200)
    organization_logo_token: str = Field(
        min_length=36,
        max_length=36,
        pattern=r"^[0-9a-f]{32}\.(jpg|png|webp)$",
    )
    database: DatabaseConfiguration
    admin: AdminSetup
    smtp: SMTPSetup | None = None


class SetupStatusResponse(APIModel):
    completed: bool
    organization_name: str | None = None


class ConnectionTestResponse(APIModel):
    success: bool
    message: str


class SetupLogoUploadResponse(APIModel):
    upload_token: str
    preview_url: str


class SMTPTestRequest(APIModel):
    smtp: SMTPSetup
    recipient: EmailStr
