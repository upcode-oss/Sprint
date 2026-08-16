from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.identity import Organization
from app.services.image_service import detect_image_mime, validate_image
from app.storage.base import ImageStorage, StoredImage


def save_staged_organization_logo(
    content: bytes,
    claimed_mime_type: str | None,
    storage: ImageStorage,
) -> StoredImage:
    mime_type = validate_image(
        content,
        claimed_mime_type,
        settings.organization_logo_max_bytes,
        error_prefix="organization_logo",
        label="Organization logo",
    )
    return storage.save(content, mime_type)


def resolve_staged_organization_logo(key: str, storage: ImageStorage) -> StoredImage:
    content = storage.read(key)
    detected = detect_image_mime(content)
    mime_type = validate_image(
        content,
        detected,
        settings.organization_logo_max_bytes,
        error_prefix="organization_logo",
        label="Organization logo",
    )
    return StoredImage(key=key, mime_type=mime_type)


def replace_organization_logo(
    db: Session,
    organization: Organization,
    content: bytes,
    claimed_mime_type: str | None,
    storage: ImageStorage,
) -> StoredImage:
    stored = save_staged_organization_logo(content, claimed_mime_type, storage)
    previous_key = organization.logo_key
    try:
        organization.logo_key = stored.key
        organization.logo_mime_type = stored.mime_type
        db.commit()
        db.refresh(organization)
    except Exception:
        db.rollback()
        storage.delete(stored.key)
        raise
    storage.delete(previous_key)
    return stored


def remove_organization_logo(
    db: Session, organization: Organization, storage: ImageStorage
) -> None:
    previous_key = organization.logo_key
    organization.logo_key = None
    organization.logo_mime_type = None
    db.commit()
    db.refresh(organization)
    storage.delete(previous_key)
