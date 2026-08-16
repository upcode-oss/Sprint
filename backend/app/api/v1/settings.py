import smtplib

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DBSession, require_permission
from app.core.config import settings
from app.core.errors import APIError
from app.core.installation import installation_store
from app.models.identity import Organization, SMTPConfiguration, User
from app.permissions.catalog import PermissionKey
from app.schemas.common import MessageResponse
from app.schemas.settings import (
    OrganizationResponse,
    OrganizationUpdate,
    SMTPConfigurationResponse,
    SMTPConfigurationUpdate,
    SystemInfoResponse,
)
from app.services.mail_service import send_email

router = APIRouter(tags=["organization", "settings"])


@router.get("/organization", response_model=OrganizationResponse)
def organization_detail(db: DBSession, current: CurrentUser) -> Organization:
    organization = db.get(Organization, current.organization_id)
    if organization is None:
        raise APIError(404, "organization_not_found", "Organization not found")
    return organization


@router.patch("/organization", response_model=OrganizationResponse)
def organization_update(
    payload: OrganizationUpdate,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.ORGANIZATION_MANAGE)),
) -> Organization:
    organization = db.get(Organization, current.organization_id)
    if organization is None:
        raise APIError(404, "organization_not_found", "Organization not found")
    organization.name = payload.name.strip()
    db.commit()
    db.refresh(organization)
    return organization


def smtp_response(configuration: SMTPConfiguration) -> SMTPConfigurationResponse:
    return SMTPConfigurationResponse(
        id=configuration.id,
        host=configuration.host,
        port=configuration.port,
        username=configuration.username,
        encryption=configuration.encryption,
        from_address=configuration.from_address,
        from_name=configuration.from_name,
        is_enabled=configuration.is_enabled,
        has_password=bool(configuration.password_encrypted),
        created_at=configuration.created_at,
        updated_at=configuration.updated_at,
    )


@router.get("/settings/smtp", response_model=SMTPConfigurationResponse | None)
def smtp_detail(
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.SETTINGS_MANAGE)),
) -> SMTPConfigurationResponse | None:
    configuration = db.scalar(
        select(SMTPConfiguration).where(
            SMTPConfiguration.organization_id == current.organization_id
        )
    )
    return smtp_response(configuration) if configuration else None


@router.put("/settings/smtp", response_model=SMTPConfigurationResponse)
def smtp_update(
    payload: SMTPConfigurationUpdate,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.SETTINGS_MANAGE)),
) -> SMTPConfigurationResponse:
    configuration = db.scalar(
        select(SMTPConfiguration).where(
            SMTPConfiguration.organization_id == current.organization_id
        )
    )
    if configuration is None:
        configuration = SMTPConfiguration(organization_id=current.organization_id)
        db.add(configuration)
    for key, value in payload.model_dump(exclude={"password"}).items():
        setattr(configuration, key, str(value) if key == "from_address" else value)
    if payload.password:
        configuration.password_encrypted = installation_store.encrypt(
            payload.password.get_secret_value()
        )
    db.commit()
    db.refresh(configuration)
    return smtp_response(configuration)


@router.post("/settings/smtp/test", response_model=MessageResponse)
def smtp_test(
    recipient: str,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.SETTINGS_MANAGE)),
) -> MessageResponse:
    configuration = db.scalar(
        select(SMTPConfiguration).where(
            SMTPConfiguration.organization_id == current.organization_id,
            SMTPConfiguration.is_enabled.is_(True),
        )
    )
    if configuration is None:
        raise APIError(409, "smtp_not_configured", "SMTP is not configured")
    try:
        send_email(configuration, recipient, "Upcode Harbor SMTP test", "SMTP is working.")
    except (OSError, smtplib.SMTPException) as exc:
        raise APIError(400, "smtp_connection_failed", "SMTP test failed") from exc
    return MessageResponse(message="Test email sent")


@router.get("/settings/system", response_model=SystemInfoResponse)
def system_info(
    _: User = Depends(require_permission(PermissionKey.SETTINGS_MANAGE)),
) -> SystemInfoResponse:
    installation = installation_store.load()
    return SystemInfoResponse(
        version="0.1.0",
        environment=settings.app_env,
        database_engine=installation.get("database_engine", "environment"),
        setup_completed=bool(installation.get("setup_completed")),
    )
