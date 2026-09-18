import smtplib
from zoneinfo import available_timezones

from fastapi import APIRouter, Depends, File, Response, UploadFile
from pydantic import EmailStr
from sqlalchemy import select

from app.api.dependencies import (
    CurrentUser,
    DBSession,
    require_permission,
    require_setup_completed,
)
from app.core.config import settings
from app.core.errors import APIError
from app.core.installation import installation_store
from app.models.identity import Organization, SMTPConfiguration, User
from app.permissions.catalog import PermissionKey
from app.schemas.common import MessageResponse
from app.schemas.settings import (
    OrganizationBrandingResponse,
    OrganizationResponse,
    OrganizationUpdate,
    SMTPConfigurationResponse,
    SMTPConfigurationUpdate,
    SystemInfoResponse,
)
from app.services.mail_service import send_email
from app.services.organization_service import remove_organization_logo, replace_organization_logo
from app.storage.local import organization_logo_storage

router = APIRouter(tags=["organization", "settings"])


def _organization(db: DBSession, organization_id: str) -> Organization:
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise APIError(404, "organization_not_found", "Organization not found")
    return organization


def _branding_response(organization: Organization) -> OrganizationBrandingResponse:
    return OrganizationBrandingResponse(
        name=organization.name,
        logo_url=organization.logo_url,
        version=settings.app_version,
    )


def _installed_organization(db: DBSession) -> Organization:
    organization = db.scalar(select(Organization))
    if organization is None:
        raise APIError(404, "organization_not_found", "Organization not found")
    return organization


@router.get("/organization", response_model=OrganizationResponse)
def organization_detail(db: DBSession, current: CurrentUser) -> Organization:
    return _organization(db, current.organization_id)


@router.get("/settings/timezones", response_model=list[str])
def timezones(_: CurrentUser) -> list[str]:
    return sorted(available_timezones())


@router.get("/organization/branding", response_model=OrganizationBrandingResponse)
def organization_branding(
    db: DBSession, _: None = Depends(require_setup_completed)
) -> OrganizationBrandingResponse:
    return _branding_response(_installed_organization(db))


@router.get("/organization/logo")
def organization_logo(
    db: DBSession, _: None = Depends(require_setup_completed)
) -> Response:
    organization = _installed_organization(db)
    if not organization.logo_key or not organization.logo_mime_type:
        raise APIError(404, "organization_logo_not_found", "Organization logo not found")
    return Response(
        content=organization_logo_storage.read(organization.logo_key),
        media_type=organization.logo_mime_type,
        headers={"Cache-Control": "private, max-age=86400", "X-Content-Type-Options": "nosniff"},
    )


@router.patch("/organization", response_model=OrganizationResponse)
def organization_update(
    payload: OrganizationUpdate,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.ORGANIZATION_MANAGE)),
) -> Organization:
    organization = _organization(db, current.organization_id)
    organization.name = payload.name.strip()
    if "timezone" in payload.model_fields_set:
        organization.timezone = payload.timezone
    db.commit()
    db.refresh(organization)
    return organization


@router.post("/organization/logo", response_model=OrganizationBrandingResponse)
async def organization_logo_upload(
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.ORGANIZATION_MANAGE)),
    logo: UploadFile = File(...),
) -> OrganizationBrandingResponse:
    organization = _organization(db, current.organization_id)
    content = await logo.read(settings.organization_logo_max_bytes + 1)
    replace_organization_logo(
        db, organization, content, logo.content_type, organization_logo_storage
    )
    return _branding_response(organization)


@router.delete("/organization/logo", response_model=OrganizationBrandingResponse)
def organization_logo_delete(
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.ORGANIZATION_MANAGE)),
) -> OrganizationBrandingResponse:
    organization = _organization(db, current.organization_id)
    remove_organization_logo(db, organization, organization_logo_storage)
    return _branding_response(organization)


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
    recipient: EmailStr,
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
        send_email(configuration, str(recipient), "Upcode sprint SMTP test", "SMTP is working.")
    except (OSError, smtplib.SMTPException) as exc:
        raise APIError(400, "smtp_connection_failed", "SMTP test failed") from exc
    return MessageResponse(message="Test email sent")


@router.get("/settings/system", response_model=SystemInfoResponse)
def system_info(
    _: User = Depends(require_permission(PermissionKey.SETTINGS_MANAGE)),
) -> SystemInfoResponse:
    installation = installation_store.load()
    return SystemInfoResponse(
        version=settings.app_version,
        environment=settings.app_env,
        database_engine=installation.get("database_engine", "environment"),
        setup_completed=bool(installation.get("setup_completed")),
    )
