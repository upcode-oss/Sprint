"""Persistent OAuth clients, consent requests, authorization codes and token digests."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MCPOAuthClient(Base):
    __tablename__ = "mcp_oauth_clients"
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    metadata_encrypted: Mapped[str] = mapped_column(Text)


class MCPOAuthRequest(Base):
    __tablename__ = "mcp_oauth_requests"
    digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("mcp_oauth_clients.id", ondelete="CASCADE"))
    data: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    csrf_digest: Mapped[str | None] = mapped_column(String(64))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MCPOAuthCode(Base):
    __tablename__ = "mcp_oauth_codes"
    digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("mcp_oauth_clients.id", ondelete="CASCADE"))
    key_id: Mapped[str] = mapped_column(ForeignKey("mcp_keys.id", ondelete="CASCADE"))
    data: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MCPOAuthToken(Base):
    __tablename__ = "mcp_oauth_tokens"
    digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(8))
    client_id: Mapped[str] = mapped_column(ForeignKey("mcp_oauth_clients.id", ondelete="CASCADE"))
    key_id: Mapped[str] = mapped_column(ForeignKey("mcp_keys.id", ondelete="CASCADE"), index=True)
    resource: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
