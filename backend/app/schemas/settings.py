from pydantic import EmailStr, Field, SecretStr

from app.schemas.common import APIModel, TimestampedResponse


class OrganizationResponse(TimestampedResponse):
    name: str


class OrganizationUpdate(APIModel):
    name: str = Field(min_length=2, max_length=200)


class SMTPConfigurationResponse(TimestampedResponse):
    host: str
    port: int
    username: str | None
    encryption: str
    from_address: EmailStr
    from_name: str
    is_enabled: bool
    has_password: bool


class SMTPConfigurationUpdate(APIModel):
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(ge=1, le=65535)
    username: str | None = Field(default=None, max_length=255)
    password: SecretStr | None = None
    encryption: str = Field(pattern=r"^(none|starttls|tls)$")
    from_address: EmailStr
    from_name: str = Field(min_length=1, max_length=200)
    is_enabled: bool = True


class SystemInfoResponse(APIModel):
    version: str
    environment: str
    database_engine: str
    setup_completed: bool
