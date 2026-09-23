from datetime import datetime
from typing import Literal
from zoneinfo import available_timezones

from pydantic import (
    AliasChoices,
    EmailStr,
    Field,
    SecretStr,
    TypeAdapter,
    field_validator,
    model_validator,
)

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


PresenceStatus = Literal["available", "away", "do_not_disturb", "offline"]
ContactType = Literal["email", "phone", "mobile"]
ContactVisibility = Literal["private", "teams", "organization"]


class PresenceResponse(APIModel):
    status: PresenceStatus
    manual_status: PresenceStatus | None
    technical_status: Literal["available", "away", "offline"]
    status_message: str | None
    status_until: datetime | None
    last_seen_at: datetime | None
    is_online: bool


class PresenceUpdate(APIModel):
    status: PresenceStatus | None = None
    status_message: str | None = Field(default=None, max_length=280)
    status_until: datetime | None = None


class UserBrief(APIModel):
    id: str
    username: str
    first_name: str
    last_name: str
    display_name: str
    avatar_url: str | None
    job_title: str | None
    department: str | None
    presence: PresenceResponse = Field(
        validation_alias=AliasChoices("presence_summary", "presence")
    )


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


class UserResponse(TimestampedResponse, UserBrief):
    email: EmailStr
    is_active: bool
    last_login: datetime | None
    roles: list[RoleBrief]


class ProfileUpdate(APIModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    display_name: str | None = Field(default=None, max_length=200)
    job_title: str | None = Field(default=None, max_length=150)
    department: str | None = Field(default=None, max_length=150)
    bio: str | None = Field(default=None, max_length=5000)
    timezone: str | None = Field(default=None, max_length=100)
    locale: str | None = Field(
        default=None, max_length=20, pattern=r"^[A-Za-z]{2,3}(?:[-_][A-Za-z]{2})?$"
    )

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Timezone cannot be empty")
        if value not in available_timezones():
            raise ValueError("Timezone must be a valid IANA timezone")
        return value


class ContactBase(APIModel):
    type: ContactType
    label: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=3, max_length=320)
    is_primary: bool = False
    visibility: ContactVisibility = "private"

    @model_validator(mode="after")
    def validate_value(self) -> "ContactBase":
        value = self.value.strip()
        if self.type == "email":
            TypeAdapter(EmailStr).validate_python(value)
        else:
            digits = sum(character.isdigit() for character in value)
            allowed = all(character.isdigit() or character in "+-(). /" for character in value)
            if digits < 5 or not allowed:
                raise ValueError("Phone contacts must contain a valid phone number")
        self.value = value
        return self


class ContactCreate(ContactBase):
    pass


class ContactUpdate(APIModel):
    type: ContactType | None = None
    label: str | None = Field(default=None, min_length=1, max_length=80)
    value: str | None = Field(default=None, min_length=3, max_length=320)
    is_primary: bool | None = None
    visibility: ContactVisibility | None = None


class ContactResponse(TimestampedResponse, ContactBase):
    pass


class NamedReference(APIModel):
    id: str
    name: str


class UserProfileResponse(UserBrief):
    bio: str | None
    contacts: list[ContactResponse]
    teams: list[NamedReference]
    projects: list[NamedReference]


class AvatarResponse(APIModel):
    avatar_url: str


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
    bio: str | None
    timezone: str
    locale: str | None
    permissions: list[str]


class ForgotPasswordRequest(APIModel):
    email: EmailStr


class ResetPasswordRequest(PasswordValidationMixin):
    token: str = Field(min_length=20)
