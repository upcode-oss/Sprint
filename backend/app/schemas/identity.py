from datetime import datetime

from pydantic import EmailStr, Field, SecretStr, field_validator

from app.schemas.common import APIModel, TimestampedResponse, UUIDString


class PermissionResponse(APIModel):
    id: str
    key: str
    description: str


class RoleBrief(APIModel):
    id: str
    name: str


class RoleCreate(APIModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    permission_keys: list[str] = Field(default_factory=list)


class RoleUpdate(APIModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    permission_keys: list[str] | None = None


class RoleResponse(TimestampedResponse):
    name: str
    description: str | None
    is_system: bool
    permissions: list[PermissionResponse]


class UserBase(APIModel):
    username: str = Field(min_length=3, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: EmailStr
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)


class PasswordValidationMixin(APIModel):
    password: SecretStr

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: SecretStr) -> SecretStr:
        plain = value.get_secret_value()
        if (
            len(plain) < 12
            or not any(c.isupper() for c in plain)
            or not any(c.islower() for c in plain)
            or not any(c.isdigit() for c in plain)
        ):
            raise ValueError("Use at least 12 characters with upper, lower and numeric characters")
        return value


class UserCreate(UserBase, PasswordValidationMixin):
    is_active: bool = True
    role_ids: list[UUIDString] = Field(default_factory=list)


class UserUpdate(APIModel):
    username: str | None = Field(
        default=None, min_length=3, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$"
    )
    email: EmailStr | None = None
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None
    role_ids: list[UUIDString] | None = None


class UserResponse(TimestampedResponse):
    username: str
    email: EmailStr
    first_name: str
    last_name: str
    is_active: bool
    last_login: datetime | None
    roles: list[RoleBrief]


class ProfileUpdate(APIModel):
    email: EmailStr | None = None
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)


class PasswordChange(PasswordValidationMixin):
    current_password: SecretStr


class LoginRequest(APIModel):
    username: str = Field(min_length=1, max_length=320)
    password: SecretStr


class TokenResponse(APIModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthUserResponse(UserResponse):
    permissions: list[str]


class ForgotPasswordRequest(APIModel):
    email: EmailStr


class ResetPasswordRequest(PasswordValidationMixin):
    token: str = Field(min_length=20)
