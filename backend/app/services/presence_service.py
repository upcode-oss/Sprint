from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import APIError
from app.models.identity import User, UserPresence
from app.schemas.identity import PresenceUpdate

PRESENCE_STATUSES = {"available", "away", "do_not_disturb", "offline"}


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def technical_presence(last_seen_at: datetime | None, now: datetime | None = None) -> str:
    now = _utc(now) or datetime.now(UTC)
    seen = _utc(last_seen_at)
    if seen is None:
        return "offline"
    seconds = max(0.0, (now - seen).total_seconds())
    if seconds >= settings.presence_offline_after:
        return "offline"
    if seconds >= settings.presence_away_after:
        return "away"
    return "available"


def presence_summary(
    presence: UserPresence | None, now: datetime | None = None
) -> dict[str, object]:
    now = _utc(now) or datetime.now(UTC)
    manual = presence.manual_status if presence else None
    until = _utc(presence.status_until) if presence else None
    if until is not None and until <= now:
        manual = None
    technical = technical_presence(presence.last_seen_at if presence else None, now)
    if manual in {"away", "do_not_disturb", "offline"}:
        effective = manual
    elif manual == "available":
        effective = technical
    else:
        effective = technical
    return {
        "status": effective,
        "manual_status": manual,
        "technical_status": technical,
        "status_message": presence.status_message if presence and manual else None,
        "status_until": until if manual else None,
        "last_seen_at": _utc(presence.last_seen_at) if presence else None,
        "is_online": technical != "offline",
    }


def ensure_presence(db: Session, user: User) -> UserPresence:
    if user.presence is None:
        user.presence = UserPresence(user_id=user.id)
        db.add(user.presence)
        db.flush()
    return user.presence


def expire_temporary_presence(db: Session, user: User, now: datetime | None = None) -> UserPresence:
    presence = ensure_presence(db, user)
    now = _utc(now) or datetime.now(UTC)
    until = _utc(presence.status_until)
    if until is not None and until <= now:
        presence.manual_status = None
        presence.status_message = None
        presence.status_until = None
        db.commit()
    return presence


def touch_presence(
    db: Session, user: User, now: datetime | None = None, *, force: bool = False
) -> bool:
    presence = ensure_presence(db, user)
    now = _utc(now) or datetime.now(UTC)
    last_seen = _utc(presence.last_seen_at)
    if (
        force
        or last_seen is None
        or (now - last_seen).total_seconds() >= settings.presence_heartbeat_interval
    ):
        presence.last_seen_at = now
        db.commit()
        return True
    return False


def update_presence(
    db: Session, user: User, payload: PresenceUpdate, now: datetime | None = None
) -> UserPresence:
    presence = ensure_presence(db, user)
    now = _utc(now) or datetime.now(UTC)
    if payload.status_until is not None and _utc(payload.status_until) <= now:
        raise APIError(422, "invalid_status_until", "Status until must be in the future")
    if "status" in payload.model_fields_set:
        presence.manual_status = payload.status
    if "status_message" in payload.model_fields_set:
        presence.status_message = payload.status_message.strip() if payload.status_message else None
    if "status_until" in payload.model_fields_set:
        presence.status_until = payload.status_until
    if presence.manual_status is None:
        presence.status_message = None
        presence.status_until = None
    db.commit()
    return presence
