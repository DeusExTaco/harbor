# app/db/models/registry.py
"""
Harbor Registry Model

Container registry configurations for Docker Hub, GHCR, and private registries.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel


if TYPE_CHECKING:
    from app.db.models.user import User


class Registry(BaseModel):
    """Container registry configuration model"""

    __tablename__ = "registries"

    # Registry identification
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        doc="Registry name (e.g., docker.io, ghcr.io)",
    )

    endpoint: Mapped[str] = mapped_column(
        String(500), nullable=False, doc="Registry endpoint URL"
    )

    # Registry type and capabilities
    registry_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="docker",
        server_default="docker",
        doc="Registry type (docker, harbor, quay, gcr, etc.)",
    )

    supports_v2: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        doc="Supports Docker Registry API v2",
    )

    supports_manifest_lists: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        doc="Supports manifest lists for multi-arch",
    )

    # Authentication
    auth_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="none",
        server_default="none",
        doc="Authentication type (none, basic, token, oauth)",
    )

    username: Mapped[str | None] = mapped_column(
        String(100), nullable=True, doc="Registry username"
    )

    password_encrypted: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="Encrypted password/token"
    )

    auth_config: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="Additional auth config (JSON)"
    )

    # Configuration
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        doc="Whether this is the default registry",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        index=True,
        doc="Whether registry is active",
    )

    timeout_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=30,
        server_default="30",
        doc="Request timeout in seconds",
    )

    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
        server_default="3",
        doc="Number of retries on failure",
    )

    retry_backoff_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
        doc="Backoff between retries",
    )

    # Rate limiting
    rate_limit_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        doc="Whether rate limiting is enforced",
    )

    rate_limit_calls_per_hour: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1000,
        server_default="1000",
        doc="Maximum API calls per hour",
    )

    # Health and monitoring
    last_health_check_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, doc="Last health check time"
    )

    health_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="unknown",
        server_default="unknown",
        doc="Health status (healthy, degraded, unhealthy, unknown)",
    )

    health_error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="Error message from last health check"
    )

    # Usage statistics
    total_queries: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        doc="Total API queries made",
    )

    successful_queries: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        doc="Successful API queries",
    )

    failed_queries: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        doc="Failed API queries",
    )

    avg_response_time_ms: Mapped[float] = mapped_column(
        Float,  # Changed from Real to Float
        nullable=False,
        default=0.0,
        server_default="0.0",
        doc="Average response time in milliseconds",
    )

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        doc="Creation timestamp",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        doc="Last update timestamp",
    )

    created_by_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        doc="User who created this registry",
    )

    # Relationships
    created_by: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[created_by_user_id],
    )

    def __repr__(self) -> str:
        return f"<Registry(id={self.id}, name='{self.name}', type='{self.registry_type}', active={self.is_active})>"

    def record_query(self, success: bool, response_time_ms: float) -> None:
        """Record a registry query result"""
        self.total_queries += 1
        if success:
            self.successful_queries += 1
        else:
            self.failed_queries += 1

        # Update average response time
        if self.total_queries > 0:
            current_total = self.avg_response_time_ms * (self.total_queries - 1)
            self.avg_response_time_ms = (
                current_total + response_time_ms
            ) / self.total_queries

    def update_health(self, status: str, error_message: str | None = None) -> None:
        """Update registry health status"""
        self.health_status = status
        self.health_error_message = error_message
        self.last_health_check_at = datetime.now(UTC)

    def get_auth_config(self) -> dict[str, Any]:
        """Get authentication configuration as dictionary"""
        import json

        if not self.auth_config:
            return {}

        try:
            return json.loads(self.auth_config)
        except json.JSONDecodeError:
            return {}

    def to_dict(self, **kwargs: Any) -> dict[str, Any]:
        """
        Convert registry to dictionary.

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

        # Never include encrypted password unless explicitly requested
        if not include_sensitive:
            exclude.add("password_encrypted")

        # Update kwargs with modified exclude set
        kwargs["exclude"] = exclude

        # Call parent with updated kwargs
        result = super().to_dict(**kwargs)

        # Parse JSON fields
        result["auth_config"] = self.get_auth_config()

        # Add statistics
        result["statistics"] = {
            "total_queries": self.total_queries,
            "successful_queries": self.successful_queries,
            "failed_queries": self.failed_queries,
            "success_rate": (
                self.successful_queries / self.total_queries * 100
                if self.total_queries > 0
                else 0
            ),
            "avg_response_time_ms": self.avg_response_time_ms,
        }

        return result
