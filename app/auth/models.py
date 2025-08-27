# app/auth/models.py
"""
Harbor Authentication Models

Data models for authentication-related operations.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    """Login request model."""

    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1)
    remember_me: bool = Field(default=False)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate and normalize username."""
        return v.strip().lower()


class LoginResponse(BaseModel):
    """Login response model."""

    success: bool
    message: str
    user: dict | None = None
    session_id: str | None = None
    csrf_token: str | None = None
    expires_at: datetime | None = None


class CreateUserRequest(BaseModel):
    """Create user request model."""

    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    email: EmailStr | None = None
    display_name: str | None = Field(None, max_length=100)
    is_admin: bool = Field(default=False)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        v = v.strip().lower()

        # Check for valid characters
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Username can only contain letters, numbers, underscores, and hyphens"
            )

        # Check for reserved names
        reserved = {"admin", "root", "harbor", "api", "system"}
        if v in reserved and v != "admin":  # Allow 'admin' for initial setup
            raise ValueError(f"Username '{v}' is reserved")

        return v


class ChangePasswordRequest(BaseModel):
    """Change password request model."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)
    confirm_password: str = Field(..., min_length=6)

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        """Validate passwords match."""
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v


class APIKeyRequest(BaseModel):
    """API key creation request model."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    expires_days: int | None = Field(None, ge=1, le=365)
    scopes: list[str] = Field(default_factory=lambda: ["admin"])


class APIKeyResponse(BaseModel):
    """API key creation response model."""

    api_key: str  # Only shown once
    key_id: int
    name: str
    created_at: datetime
    expires_at: datetime | None
    warning: str = "⚠️ This key will only be shown once. Store it securely!"


class UserInfo(BaseModel):
    """User information model."""

    id: int
    username: str
    email: str | None
    display_name: str | None
    is_admin: bool
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None
    login_count: int = 0
    failed_login_count: int = 0
