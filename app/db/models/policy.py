# app/db/models/policy.py
"""
Harbor Container Policy Model

Container-specific update policies and configuration.
Inherits from global defaults with per-container overrides.

FIXED: Added proper imports to fix F821 errors for Container and User models
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel


class ContainerPolicy(BaseModel):
    """
    Container-specific update policy configuration

    Defines how and when a specific container should be updated.
    Inherits from global defaults with per-container overrides.
    """

    __tablename__ = "container_policies"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    container_uid: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("containers.uid", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Update policy
    desired_version: Mapped[str] = mapped_column(
        String(100), default="latest", nullable=False
    )
    update_strategy: Mapped[str] = mapped_column(
        String(20), default="rolling", nullable=False
    )

    # Scheduling policy
    check_interval_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    update_time: Mapped[str | None] = mapped_column(
        String(5), nullable=True
    )  # HH:MM format
    update_timezone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    update_days: Mapped[str] = mapped_column(
        Text, default="[]", nullable=False
    )  # JSON array

    # Behavior flags
    exclude_from_updates: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    auto_update_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )
    stay_stopped: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dry_run_only: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    require_approval: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Safety and rollback
    health_check_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    health_check_timeout_seconds: Mapped[int] = mapped_column(
        Integer, default=60, nullable=False
    )
    health_check_retries: Mapped[int] = mapped_column(
        Integer, default=3, nullable=False
    )
    rollback_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    rollback_timeout_seconds: Mapped[int] = mapped_column(
        Integer, default=300, nullable=False
    )

    # Cleanup policy
    cleanup_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cleanup_keep_images: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    cleanup_delay_hours: Mapped[int] = mapped_column(
        Integer, default=24, nullable=False
    )

    # Notification preferences (future)
    notify_on_update: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    notify_on_failure: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    notification_channels: Mapped[str] = mapped_column(
        Text, default="[]", nullable=False
    )  # JSON array

    # Advanced options
    pull_timeout_seconds: Mapped[int] = mapped_column(
        Integer, default=300, nullable=False
    )
    create_timeout_seconds: Mapped[int] = mapped_column(
        Integer, default=60, nullable=False
    )
    stop_timeout_seconds: Mapped[int] = mapped_column(
        Integer, default=30, nullable=False
    )

    # Priority and dependencies (future)
    update_priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    depends_on_containers: Mapped[str] = mapped_column(
        Text, default="[]", nullable=False
    )  # JSON array

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )

    # Relationships - FIXED: Import models at top
    from app.db.models.container import Container
    from app.db.models.user import User

    container: Mapped[Container] = relationship("Container", back_populates="policy")
    created_by_user: Mapped[User | None] = relationship(
        "User", foreign_keys=[created_by_user_id]
    )

    def __repr__(self) -> str:
        return f"<ContainerPolicy(container_uid='{self.container_uid}', auto_update={self.auto_update_enabled})>"

    def __str__(self) -> str:
        return f"Policy for container {self.container_uid}"

    def is_eligible_for_update(self) -> bool:
        """Check if container is eligible for updates"""
        return (
            self.auto_update_enabled
            and not self.exclude_from_updates
            and not self.dry_run_only
        )

    def get_update_days(self) -> list[str]:
        """Get update days as list"""
        import json

        if not self.update_days:
            return []

        try:
            days = json.loads(self.update_days)
            return days if isinstance(days, list) else []
        except json.JSONDecodeError:
            return []

    def set_update_days(self, days: list[str]) -> None:
        """Set update days from list"""
        import json

        # Validate days
        valid_days = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]
        filtered_days = [day.lower() for day in days if day.lower() in valid_days]

        self.update_days = json.dumps(filtered_days, sort_keys=True)
        self.update_timestamp()

    def get_notification_channels(self) -> list[str]:
        """Get notification channels as list"""
        import json

        if not self.notification_channels:
            return []

        try:
            channels = json.loads(self.notification_channels)
            return channels if isinstance(channels, list) else []
        except json.JSONDecodeError:
            return []

    def set_notification_channels(self, channels: list[str]) -> None:
        """Set notification channels from list"""
        import json

        self.notification_channels = json.dumps(channels, sort_keys=True)
        self.update_timestamp()

    def get_depends_on_containers(self) -> list[str]:
        """Get dependency container UIDs as list"""
        import json

        if not self.depends_on_containers:
            return []

        try:
            deps = json.loads(self.depends_on_containers)
            return deps if isinstance(deps, list) else []
        except json.JSONDecodeError:
            return []

    def set_depends_on_containers(self, container_uids: list[str]) -> None:
        """Set dependency container UIDs from list"""
        import json

        self.depends_on_containers = json.dumps(container_uids, sort_keys=True)
        self.update_timestamp()

    def should_update_on_day(self, day_name: str) -> bool:
        """Check if updates are allowed on a specific day"""
        update_days = self.get_update_days()
        if not update_days:
            return True  # No restrictions means updates allowed any day
        return day_name.lower() in update_days

    def to_dict(self, include_timestamps: bool = True) -> dict[str, Any]:
        """Convert to dictionary - matching parent signature"""
        result = super().to_dict(include_timestamps=include_timestamps)

        # Add parsed JSON fields
        result["update_days"] = self.get_update_days()
        result["notification_channels"] = self.get_notification_channels()
        result["depends_on_containers"] = self.get_depends_on_containers()

        return result

    @classmethod
    def create_default_policy(cls, container_uid: str) -> "ContainerPolicy":
        """Create a default policy for a container"""
        return cls(
            container_uid=container_uid,
            desired_version="latest",
            update_strategy="rolling",
            auto_update_enabled=True,
            exclude_from_updates=False,
            health_check_enabled=True,
            rollback_enabled=True,
            cleanup_enabled=True,
        )
