# app/db/models/api_key.py
"""
Harbor API Key Model

API key model for programmatic access with proper typing.
"""

from __future__ import annotations

import json
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

    # Future: Scoped permissions - stored as JSON string
    _scopes: Mapped[str] = mapped_column(
        "scopes",
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

    @property
    def scopes(self) -> list[str]:
        """Get scopes as a Python list"""
        try:
            return json.loads(self._scopes) if self._scopes else ["admin"]
        except (json.JSONDecodeError, TypeError):
            return ["admin"]

    @scopes.setter
    def scopes(self, value: list[str] | str | None) -> None:
        """Set scopes from a list or JSON string"""
        if value is None:
            self._scopes = '["admin"]'
        elif isinstance(value, str):
            # If it's already a JSON string, validate it
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    self._scopes = value
                else:
                    self._scopes = '["admin"]'
            except json.JSONDecodeError:
                self._scopes = '["admin"]'
        else:  # This must be a list[str] based on type hint
            # Convert list to JSON string
            # Validate scopes
            valid_scopes = ["admin", "read", "write", "containers", "users"]
            filtered = [s for s in value if s in valid_scopes]
            if not filtered:
                filtered = ["admin"]
            self._scopes = json.dumps(filtered, sort_keys=True)

        # Update timestamp when scopes change
        if hasattr(self, "update_timestamp"):
            self.update_timestamp()

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
        """Get API key scopes as list (alias for property)"""
        return self.scopes

    def set_scopes(self, scopes: list[str]) -> None:
        """Set API key scopes from list (uses property setter)"""
        self.scopes = scopes

    def has_scope(self, scope: str) -> bool:
        """Check if API key has specific scope"""
        current_scopes = self.scopes
        return (
            scope in current_scopes or "admin" in current_scopes
        )  # Admin has all scopes

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

    def to_dict(self, **kwargs: Any) -> dict[str, Any]:
        """
        Convert API key to dictionary.

        Args:
            **kwargs: Options including:
                - include_sensitive: Whether to include sensitive fields
                - exclude: Set of fields to exclude
                - include_timestamps: Whether to include timestamps

        Returns:
            Dictionary representation
        """
        include_sensitive = kwargs.get("include_sensitive", False)
        exclude = set(kwargs.get("exclude", set()))

        # Never include the actual key hash
        if not include_sensitive:
            exclude.add("key_hash")

        # Exclude the internal _scopes field
        exclude.add("_scopes")

        # Update kwargs with modified exclude set
        kwargs["exclude"] = exclude

        # Call parent with updated kwargs
        result = super().to_dict(**kwargs)

        # Add the parsed scopes
        result["scopes"] = self.scopes

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
            "scopes": self.scopes,  # Uses the property
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
