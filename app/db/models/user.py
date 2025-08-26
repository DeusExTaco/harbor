# app/db/models/user.py
"""
Harbor User Model

User model for authentication and authorization with proper relationship definitions.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel


if TYPE_CHECKING:
    # Import only for type checking to avoid circular dependency at runtime
    # This is a standard pattern in Python for handling circular imports
    # CodeQL may flag this but it's a false positive - TYPE_CHECKING ensures
    # this import never happens at runtime, preventing actual circular imports
    from app.db.models.api_key import APIKey


class User(BaseModel):
    """User model for authentication and authorization"""

    __tablename__ = "users"

    # Basic authentication fields
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique username for authentication",
    )

    email: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True, index=True, doc="User email address"
    )

    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False, doc="Argon2id password hash"
    )

    # Profile information
    display_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, doc="Display name for UI"
    )

    timezone: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="UTC",
        server_default="UTC",
        doc="User timezone preference",
    )

    # Authentication tracking
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, doc="Last successful login timestamp"
    )

    login_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        doc="Number of successful logins",
    )

    # Account status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        index=True,
        doc="Whether account is active",
    )

    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        doc="Whether user has admin privileges",
    )

    # Future: MFA support (ready but disabled in v1)
    mfa_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        doc="Whether MFA is enabled (future)",
    )

    mfa_secret: Mapped[str | None] = mapped_column(
        String(32), nullable=True, doc="TOTP secret in base32 encoding (future)"
    )

    mfa_backup_codes: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="JSON array of backup codes (future)"
    )

    # Future: RBAC support
    roles: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default='["admin"]',
        server_default='["admin"]',
        doc="JSON array of roles (future)",
    )

    # Preferences
    preferences: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
        server_default="{}",
        doc="JSON user preferences object",
    )

    # Relationships
    # Use string annotation for forward reference to avoid circular imports
    # SQLAlchemy resolves "APIKey" string at runtime after all models are loaded
    api_keys: Mapped[list[APIKey]] = relationship(
        "APIKey",  # String reference for SQLAlchemy's lazy resolution
        back_populates="created_by",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<User(id={self.id}, username='{self.username}', admin={self.is_admin})>"
        )

    def record_login(self) -> None:
        """Record successful login attempt"""
        # Initialize login_count if it's None (for existing records)
        if self.login_count is None:
            self.login_count = 0

        self.login_count += 1
        self.last_login_at = datetime.now(UTC)
        self.update_timestamp()

    def get_roles(self) -> list[str]:
        """Get user roles as list"""
        try:
            roles = json.loads(self.roles or '["admin"]')
            if isinstance(roles, list):
                return roles
            return ["admin"] if self.is_admin else []
        except json.JSONDecodeError:
            return ["admin"] if self.is_admin else []

    def set_roles(self, roles: list[str]) -> None:
        """Set user roles from list"""
        self.roles = json.dumps(roles, sort_keys=True)
        self.update_timestamp()

    def has_role(self, role: str) -> bool:
        """Check if user has specific role"""
        return role in self.get_roles() or (role == "admin" and self.is_admin)

    def get_preferences(self) -> dict[str, Any]:
        """Get user preferences as dictionary"""
        try:
            prefs = json.loads(self.preferences or "{}")
            if isinstance(prefs, dict):
                return prefs
            return {}
        except json.JSONDecodeError:
            return {}

    def set_preferences(self, preferences: dict[str, Any]) -> None:
        """Set user preferences from dictionary"""
        self.preferences = json.dumps(preferences, sort_keys=True)
        self.update_timestamp()

    def update_preference(self, key: str, value: Any) -> None:
        """Update single preference value"""
        prefs = self.get_preferences()
        prefs[key] = value
        self.set_preferences(prefs)

    def get_mfa_backup_codes(self) -> list[str]:
        """Get MFA backup codes as list"""
        if not self.mfa_backup_codes:
            return []

        try:
            codes = json.loads(self.mfa_backup_codes)
            if isinstance(codes, list):
                return codes
            return []
        except json.JSONDecodeError:
            return []

    def set_mfa_backup_codes(self, codes: list[str]) -> None:
        """Set MFA backup codes from list"""
        self.mfa_backup_codes = json.dumps(codes, sort_keys=True)
        self.update_timestamp()

    def to_dict(self, include_sensitive: bool = False) -> dict[str, Any]:
        """Convert user to dictionary"""
        result = super().to_dict()

        # Never include password hash
        result.pop("password_hash", None)

        # Remove sensitive MFA data unless requested
        if not include_sensitive:
            result.pop("mfa_secret", None)
            result.pop("mfa_backup_codes", None)

        # Parse JSON fields
        result["roles"] = self.get_roles()
        result["preferences"] = self.get_preferences()

        return result

    def to_summary_dict(self) -> dict[str, Any]:
        """Get user summary for listings"""
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name or self.username,
            "email": self.email,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "last_login_at": self.last_login_at.isoformat()
            if self.last_login_at
            else None,
        }
