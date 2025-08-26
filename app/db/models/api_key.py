# app/db/models/api_key.py
"""
Harbor API Key Model

API key model for programmatic access with proper typing.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel


if TYPE_CHECKING:
    from app.db.models.user import User


class APIKey(BaseModel):
    """API key model for programmatic access"""

    __tablename__ = "api_keys"

    # Key identification
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="default",
        server_default="default",
        doc="Human readable key name",
    )

    key_hash: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="Hashed API key (SHA-256)",
    )

    # Key metadata
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="Key description or purpose"
    )

    created_by_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="User who created this key",
    )

    # Usage tracking
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, doc="Last time key was used"
    )

    last_used_ip: Mapped[str | None] = mapped_column(
        String(45),  # IPv6 compatible
        nullable=True,
        doc="Last IP address that used this key",
    )

    usage_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", doc="Total usage count"
    )

    # Key lifecycle
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Key expiration time (NULL = never expires)",
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Key revocation time (NULL = not revoked)",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        index=True,
        doc="Whether key is active",
    )

    # Future: Scoped permissions
    scopes: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default='["admin"]',
        server_default='["admin"]',
        doc="JSON array of scopes (future)",
    )

    rate_limit_per_hour: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1000,
        server_default="1000",
        doc="Rate limit per hour",
    )

    # Relationships - Use forward reference (string in quotes)
    created_by: Mapped[User] = relationship(
        "User",  # String reference for SQLAlchemy
        back_populates="api_keys",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<APIKey(id={self.id}, name='{self.name}', active={self.is_active})>"

    def record_usage(self, ip_address: str | None = None) -> None:
        """Record API key usage"""
        self.last_used_at = datetime.now(UTC)
        self.usage_count += 1
        if ip_address:
            self.last_used_ip = ip_address
        self.update_timestamp()

    def revoke(self) -> None:
        """Revoke the API key"""
        self.is_active = False
        self.revoked_at = datetime.now(UTC)
        self.update_timestamp()

    def get_scopes(self) -> list[str]:
        """Get API key scopes as list"""
        import json

        try:
            scopes = json.loads(self.scopes or '["admin"]')
            if isinstance(scopes, list):
                return scopes
            return ["admin"]
        except json.JSONDecodeError:
            return ["admin"]

    def set_scopes(self, scopes: list[str]) -> None:
        """Set API key scopes from list"""
        import json

        # Validate scopes (basic validation)
        valid_scopes = [
            "admin",
            "read",
            "write",
            "containers",
            "users",
        ]  # Add more as needed
        filtered_scopes = [scope for scope in scopes if scope in valid_scopes]
        if not filtered_scopes:
            filtered_scopes = ["admin"]  # Default to admin

        self.scopes = json.dumps(filtered_scopes, sort_keys=True)
        self.update_timestamp()

    def has_scope(self, scope: str) -> bool:
        """Check if API key has specific scope"""
        scopes = self.get_scopes()
        return scope in scopes or "admin" in scopes  # Admin has all scopes

    def is_expired(self) -> bool:
        """Check if API key is expired"""
        if not self.expires_at:
            return False
        return datetime.now(UTC) > self.expires_at

    def is_revoked(self) -> bool:
        """Check if API key is revoked"""
        return self.revoked_at is not None

    def is_valid(self) -> bool:
        """Check if API key is valid for use"""
        return self.is_active and not self.is_expired() and not self.is_revoked()

    def to_dict(self, include_sensitive: bool = False) -> dict[str, Any]:
        """Convert API key to dictionary"""
        result = super().to_dict()

        # Never include the actual key hash
        result.pop("key_hash", None)

        # Parse JSON fields
        result["scopes"] = self.get_scopes()

        # Add computed fields
        result["is_expired"] = self.is_expired()
        result["is_revoked"] = self.is_revoked()
        result["is_valid"] = self.is_valid()

        # Add usage statistics
        result["usage_statistics"] = {
            "usage_count": self.usage_count,
            "last_used_at": self.last_used_at.isoformat()
            if self.last_used_at
            else None,
            "last_used_ip": self.last_used_ip,
            "rate_limit_per_hour": self.rate_limit_per_hour,
        }

        return result

    def to_summary_dict(self) -> dict[str, Any]:
        """Get API key summary for listings"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "is_valid": self.is_valid(),
            "created_at": self.created_at.isoformat(),
            "last_used_at": self.last_used_at.isoformat()
            if self.last_used_at
            else None,
            "usage_count": self.usage_count,
            "scopes": self.get_scopes(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
