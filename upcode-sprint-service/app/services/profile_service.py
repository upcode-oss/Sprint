from sqlalchemy import exists, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import APIError
from app.models.associations import project_teams, team_members
from app.models.identity import User, UserContact, UserProfile
from app.models.project import Project, Team
from app.permissions.catalog import PermissionKey
from app.schemas.identity import ContactCreate, ContactUpdate, ProfileUpdate
from app.services.image_service import detect_image_mime, validate_image
from app.services.permission_service import effective_permission_keys, is_admin
from app.storage.base import AvatarStorage, StoredAvatar


def ensure_profile(db: Session, user: User) -> UserProfile:
    if user.profile is None:
        user.profile = UserProfile(user_id=user.id, timezone="UTC")
        db.add(user.profile)
        db.flush()
    return user.profile


def update_profile(db: Session, user: User, payload: ProfileUpdate) -> User:
    profile = ensure_profile(db, user)
    values = payload.model_dump(exclude_unset=True)
    for key in ("first_name", "last_name"):
        if key in values:
            setattr(user, key, values.pop(key).strip())
    for key, value in values.items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(profile, key, value)
    db.commit()
    return user


def _normalize_contact_value(contact_type: str, value: str) -> str:
    value = value.strip()
    return value.lower() if contact_type == "email" else value


def _clear_primary(db: Session, user_id: str, contact_type: str, except_id: str | None) -> None:
    statement = update(UserContact).where(
        UserContact.user_id == user_id,
        UserContact.type == contact_type,
        UserContact.is_primary.is_(True),
    )
    if except_id:
        statement = statement.where(UserContact.id != except_id)
    db.execute(statement.values(is_primary=False, primary_slot=None))


def create_contact(db: Session, user: User, payload: ContactCreate) -> UserContact:
    if payload.is_primary:
        _clear_primary(db, user.id, payload.type, None)
    contact = UserContact(
        user_id=user.id,
        type=payload.type,
        label=payload.label.strip(),
        value=_normalize_contact_value(payload.type, payload.value),
        is_primary=payload.is_primary,
        primary_slot="primary" if payload.is_primary else None,
        visibility=payload.visibility,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def get_contact(db: Session, user: User, contact_id: str) -> UserContact:
    contact = db.scalar(
        select(UserContact).where(UserContact.id == contact_id, UserContact.user_id == user.id)
    )
    if contact is None:
        raise APIError(404, "contact_not_found", "Contact information not found")
    return contact


def update_contact(
    db: Session, user: User, contact: UserContact, payload: ContactUpdate
) -> UserContact:
    values = payload.model_dump(exclude_unset=True)
    candidate = ContactCreate(
        type=values.get("type", contact.type),
        label=values.get("label", contact.label),
        value=values.get("value", contact.value),
        is_primary=values.get("is_primary", contact.is_primary),
        visibility=values.get("visibility", contact.visibility),
    )
    if candidate.is_primary:
        _clear_primary(db, user.id, candidate.type, contact.id)
    for key, value in candidate.model_dump().items():
        if key == "value":
            value = _normalize_contact_value(candidate.type, value)
        elif key == "label":
            value = value.strip()
        setattr(contact, key, value)
    contact.primary_slot = "primary" if candidate.is_primary else None
    db.commit()
    db.refresh(contact)
    return contact


def delete_contact(db: Session, contact: UserContact) -> None:
    db.delete(contact)
    db.commit()


def users_share_team(db: Session, first_user_id: str, second_user_id: str) -> bool:
    first_membership = team_members.alias("first_membership")
    second_membership = team_members.alias("second_membership")
    return bool(
        db.scalar(
            select(
                exists()
                .where(first_membership.c.user_id == first_user_id)
                .where(second_membership.c.user_id == second_user_id)
                .where(first_membership.c.team_id == second_membership.c.team_id)
            )
        )
    )


def may_view_private_contacts(viewer: User, target: User) -> bool:
    permissions = effective_permission_keys(viewer)
    return (
        viewer.id == target.id
        or is_admin(viewer)
        or PermissionKey.USERS_CONTACTS_VIEW.value in permissions
    )


def visible_contacts(db: Session, viewer: User, target: User) -> list[UserContact]:
    contacts = list(
        db.scalars(
            select(UserContact)
            .where(UserContact.user_id == target.id)
            .order_by(UserContact.type, UserContact.is_primary.desc(), UserContact.created_at)
        )
    )
    if may_view_private_contacts(viewer, target):
        return contacts
    shared_team = users_share_team(db, viewer.id, target.id)
    allowed = {"organization", "teams"} if shared_team else {"organization"}
    return [contact for contact in contacts if contact.visibility in allowed]


def user_teams_and_projects(
    db: Session, viewer: User, target: User
) -> tuple[list[Team], list[Project]]:
    target_membership = team_members.alias("target_membership")
    teams_statement = (
        select(Team)
        .join(target_membership, target_membership.c.team_id == Team.id)
        .where(target_membership.c.user_id == target.id)
    )
    projects_statement = (
        select(Project)
        .join(project_teams, project_teams.c.project_id == Project.id)
        .join(target_membership, target_membership.c.team_id == project_teams.c.team_id)
        .where(target_membership.c.user_id == target.id)
    )
    if viewer.id != target.id and not is_admin(viewer):
        viewer_membership = team_members.alias("viewer_membership")
        visible_team_ids = select(viewer_membership.c.team_id).where(
            viewer_membership.c.user_id == viewer.id
        )
        teams_statement = teams_statement.where(Team.id.in_(visible_team_ids))
        visible_project_ids = (
            select(project_teams.c.project_id)
            .join(
                viewer_membership,
                viewer_membership.c.team_id == project_teams.c.team_id,
            )
            .where(viewer_membership.c.user_id == viewer.id)
        )
        projects_statement = projects_statement.where(Project.id.in_(visible_project_ids))
    teams = list(db.scalars(teams_statement.order_by(Team.name).distinct()))
    projects = list(db.scalars(projects_statement.order_by(Project.name).distinct()))
    return teams, projects


def detect_avatar_mime(content: bytes) -> str | None:
    return detect_image_mime(content)


def validate_avatar(content: bytes, claimed_mime_type: str | None) -> str:
    return validate_image(
        content,
        claimed_mime_type,
        settings.avatar_max_bytes,
        error_prefix="avatar",
        label="Avatar",
    )


def save_avatar(
    db: Session,
    user: User,
    content: bytes,
    claimed_mime_type: str | None,
    storage: AvatarStorage,
) -> StoredAvatar:
    mime_type = validate_avatar(content, claimed_mime_type)
    profile = ensure_profile(db, user)
    previous_key = profile.avatar_key
    stored = storage.save(content, mime_type)
    try:
        profile.avatar_key = stored.key
        profile.avatar_mime_type = stored.mime_type
        db.commit()
    except Exception:
        db.rollback()
        storage.delete(stored.key)
        raise
    storage.delete(previous_key)
    return stored


def remove_avatar(db: Session, user: User, storage: AvatarStorage) -> None:
    profile = ensure_profile(db, user)
    previous_key = profile.avatar_key
    profile.avatar_key = None
    profile.avatar_mime_type = None
    db.commit()
    storage.delete(previous_key)
