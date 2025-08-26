# app/db/models/settings.py
"""
Harbor System Settings Model - FIXED __table_args__ INHERITANCE

Singleton model for global system configuration with profile-aware defaults.
SQLite compatible constraints and proper default value handling.
"""

from typing import Any

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.config import DeploymentProfile
from app.db.base import SingletonModel


class SystemSettings(SingletonModel):
    """System-wide settings singleton model"""

    __tablename__ = "system_settings"

    # Default update policies
    default_check_interval_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=86400,  # 24 hours
        server_default="86400",
        doc="Default interval between update checks (min: 60)",
    )

    default_update_time: Mapped[str] = mapped_column(
        String(5),
        nullable=False,
        default="03:00",
        server_default="03:00",
        doc="Default time for scheduled updates (HH:MM)",
    )

    default_timezone: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="UTC",
        server_default="UTC",
        doc="Default timezone for scheduling",
    )

    default_cleanup_keep_images: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=2,
        server_default="2",
        doc="Default number of old images to keep (min: 0)",
    )

    # Global control flags
    global_pause_updates: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        doc="Pause all automatic updates",
    )

    global_dry_run_mode: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        doc="Run all operations in dry-run mode",
    )

    emergency_stop: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        doc="Emergency stop all operations",
    )

    maintenance_mode: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        doc="System maintenance mode",
    )

    # Update windows and scheduling
    maintenance_window_start: Mapped[str | None] = mapped_column(
        String(5), nullable=True, doc="Maintenance window start time (HH:MM)"
    )

    maintenance_window_end: Mapped[str | None] = mapped_column(
        String(5), nullable=True, doc="Maintenance window end time (HH:MM)"
    )

    maintenance_days: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
        server_default="[]",
        doc="JSON array of maintenance days",
    )

    blackout_periods: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
        server_default="[]",
        doc="JSON array of blackout periods",
    )

    # Rate limiting and concurrency
    max_concurrent_updates: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
        server_default="5",
        doc="Maximum concurrent update operations (min: 1)",
    )

    update_delay_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        doc="Delay between starting concurrent updates",
    )

    rate_limit_registry_calls: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
        server_default="100",
        doc="Registry API calls per hour limit",
    )

    # Resource limits
    max_memory_usage_mb: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=512,
        server_default="512",
        doc="Maximum memory usage in MB",
    )

    max_disk_usage_gb: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        server_default="10",
        doc="Maximum disk usage in GB",
    )

    max_log_retention_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=30,
        server_default="30",
        doc="Maximum log retention in days",
    )

    # Feature flags (v1.0 - basic features enabled)
    enable_auto_discovery: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        doc="Enable automatic container discovery",
    )

    enable_metrics: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        doc="Enable Prometheus metrics",
    )

    enable_health_checks: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        doc="Enable health check monitoring",
    )

    enable_cleanup: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        doc="Enable automatic cleanup",
    )

    enable_notifications: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        doc="Enable notifications (future)",
    )

    enable_audit_export: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        doc="Enable audit export (future)",
    )

    # Home lab specific features
    show_getting_started: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        doc="Show getting started wizard",
    )

    enable_simple_mode: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        doc="Enable simplified UI mode",
    )

    auto_exclude_harbor: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        doc="Automatically exclude Harbor from updates",
    )

    # Security settings
    require_https: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        doc="Require HTTPS for all requests",
    )

    session_timeout_hours: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=168,  # 1 week for home lab
        server_default="168",
        doc="Session timeout in hours",
    )

    api_rate_limit_per_hour: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1000,
        server_default="1000",
        doc="API requests per hour limit",
    )

    # Deployment profile
    deployment_profile: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="homelab",
        server_default="homelab",
        doc="Current deployment profile",
    )

    # REMOVED __table_args__ - singleton constraint is inherited from SingletonModel
    # Additional validation constraints should be enforced in business logic
    # or as column-level constraints in the doc strings

    def __repr__(self) -> str:
        return f"<SystemSettings(profile={self.deployment_profile})>"

    def validate(self) -> None:
        """Validate settings constraints that can't be enforced at DB level"""
        if self.default_check_interval_seconds < 60:
            raise ValueError("Check interval must be at least 60 seconds")
        if self.max_concurrent_updates < 1:
            raise ValueError("Must allow at least 1 concurrent update")
        if self.default_cleanup_keep_images < 0:
            raise ValueError("Cleanup keep images must be non-negative")

    def apply_profile_defaults(self, profile: DeploymentProfile) -> None:
        """Apply profile-specific defaults"""
        if profile == DeploymentProfile.HOMELAB:
            self.max_concurrent_updates = 2
            self.session_timeout_hours = 168  # 1 week
            self.require_https = False
            self.show_getting_started = True
            self.enable_simple_mode = True

        elif profile == DeploymentProfile.DEVELOPMENT:
            self.max_concurrent_updates = 3
            self.session_timeout_hours = 72  # 3 days
            self.require_https = False
            self.show_getting_started = True

        elif profile == DeploymentProfile.PRODUCTION:
            self.max_concurrent_updates = 10
            self.session_timeout_hours = 8  # 8 hours
            self.require_https = True
            self.show_getting_started = False
            self.enable_simple_mode = False

        # Update deployment profile
        self.deployment_profile = profile.value
        self.update_timestamp()

    def get_maintenance_days(self) -> list[str]:
        """Get maintenance days as list"""
        import json

        if not self.maintenance_days:
            return []

        try:
            days = json.loads(self.maintenance_days)
            return days if isinstance(days, list) else []
        except json.JSONDecodeError:
            return []

    def set_maintenance_days(self, days: list[str]) -> None:
        """Set maintenance days from list"""
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

        self.maintenance_days = json.dumps(filtered_days, sort_keys=True)
        self.update_timestamp()

    def get_blackout_periods(self) -> list[dict[str, str]]:
        """Get blackout periods as list"""
        import json

        if not self.blackout_periods:
            return []

        try:
            periods = json.loads(self.blackout_periods)
            return periods if isinstance(periods, list) else []
        except json.JSONDecodeError:
            return []

    def set_blackout_periods(self, periods: list[dict[str, str]]) -> None:
        """Set blackout periods from list"""
        import json

        self.blackout_periods = json.dumps(periods, sort_keys=True)
        self.update_timestamp()

    def is_in_maintenance_window(self) -> bool:
        """Check if current time is in maintenance window"""
        if not self.maintenance_window_start or not self.maintenance_window_end:
            return False

        from datetime import datetime, time

        now = datetime.now().time()
        start_time = time.fromisoformat(self.maintenance_window_start)
        end_time = time.fromisoformat(self.maintenance_window_end)

        if start_time <= end_time:
            # Same day window
            return start_time <= now <= end_time
        else:
            # Overnight window
            return now >= start_time or now <= end_time

    def is_maintenance_day(self) -> bool:
        """Check if today is a maintenance day"""
        maintenance_days = self.get_maintenance_days()
        if not maintenance_days:
            return True  # No restrictions

        from datetime import datetime

        today = datetime.now().strftime("%A").lower()
        return today in maintenance_days

    def can_perform_updates(self) -> bool:
        """Check if updates can be performed based on settings"""
        if self.global_pause_updates or self.emergency_stop or self.maintenance_mode:
            return False

        return self.is_maintenance_day() and self.is_in_maintenance_window()

    def to_dict(self, **kwargs: Any) -> dict[str, Any]:
        """
        Convert to dictionary.

        Args:
            **kwargs: Options including:
                - exclude: Set of fields to exclude
                - include_timestamps: Whether to include timestamps

        Returns:
            Dictionary representation
        """
        # Call parent with kwargs
        result = super().to_dict(**kwargs)

        # Add parsed JSON fields
        result["maintenance_days"] = self.get_maintenance_days()
        result["blackout_periods"] = self.get_blackout_periods()

        return result
