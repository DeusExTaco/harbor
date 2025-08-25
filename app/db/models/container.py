# app/db/models/container.py
"""
Harbor Container Model - FIXED TYPE ANNOTATIONS

Container discovery and management model with SQLite-compatible constraints
and comprehensive state tracking for automatic updates.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel


if TYPE_CHECKING:
    from app.db.models.policy import ContainerPolicy


class Container(BaseModel):
    """Container model for discovery and management tracking"""

    __tablename__ = "containers"

    # Stable identification
    uid: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
        index=True,
        doc="Stable UUID for container reference",
    )

    docker_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True, doc="Current Docker container ID"
    )

    docker_name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, doc="Docker container name"
    )

    # Image information
    image_repo: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
        doc="Image repository (e.g., nginx, library/redis)",
    )

    image_tag: Mapped[str] = mapped_column(
        String(100), nullable=False, doc="Image tag (e.g., latest, 1.21-alpine)"
    )

    image_ref: Mapped[str] = mapped_column(
        String(600), nullable=False, doc="Full image reference (nginx:1.21-alpine)"
    )

    current_digest: Mapped[str | None] = mapped_column(
        String(71),  # sha256: + 64 hex chars
        nullable=True,
        doc="Current image digest (sha256:...)",
    )

    # Container state
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        doc="Container status (running, stopped, created, etc.)",
    )

    desired_state: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="running",
        server_default="running",
        doc="Desired container state",
    )

    # Discovery tracking
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        doc="When container was first discovered",
    )

    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        doc="When container was last seen during discovery",
    )

    last_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, doc="When container was last updated"
    )

    # Management flags
    managed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        index=True,
        doc="Whether container is managed by Harbor",
    )

    auto_discovered: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        doc="Whether container was auto-discovered",
    )

    # Container configuration (JSON fields)
    labels: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
        server_default="{}",
        doc="Docker labels (JSON)",
    )

    environment: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
        server_default="{}",
        doc="Environment variables (JSON)",
    )

    ports: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
        server_default="[]",
        doc="Port mappings (JSON)",
    )

    volumes: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
        server_default="[]",
        doc="Volume mounts (JSON)",
    )

    networks: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
        server_default="[]",
        doc="Network connections (JSON)",
    )

    # Full container specification for recreation
    container_spec: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="Complete container configuration (JSON)"
    )

    # Update statistics
    update_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        doc="Number of updates performed",
    )

    last_update_duration_ms: Mapped[int | None] = mapped_column(
        Integer, nullable=True, doc="Duration of last update in milliseconds"
    )

    last_update_success: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, doc="Whether last update was successful"
    )

    # FIXED: SQLite compatible constraints (removed PostgreSQL regex operators)
    __table_args__ = (
        # Removed the regex constraint that was causing SQLite errors
        # UUID validation will be handled at application level
        CheckConstraint("length(uid) = 36", name="check_uid_length"),
        CheckConstraint(
            "status IN ('running', 'stopped', 'created', 'restarting', 'removing', 'paused', 'exited', 'dead', 'missing')",
            name="check_valid_status",
        ),
        CheckConstraint(
            "desired_state IN ('running', 'stopped')", name="check_valid_desired_state"
        ),
    )

    # Relationships
    policy: Mapped[Optional["ContainerPolicy"]] = relationship(
        "ContainerPolicy",
        back_populates="container",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Container(id={self.id}, uid='{self.uid}', name='{self.docker_name}', status='{self.status}')>"

    def update_last_seen(self) -> None:
        """Update last seen timestamp"""
        self.last_seen_at = datetime.now(UTC)
        self.update_timestamp()

    def record_update(self, success: bool, duration_ms: int) -> None:
        """Record update attempt"""
        self.last_update_success = success
        self.last_update_duration_ms = duration_ms
        self.last_updated_at = datetime.now(UTC)

        if success:
            self.update_count += 1

        self.update_timestamp()

    def get_labels(self) -> dict[str, str]:
        """Get container labels as dictionary"""
        import json

        if not self.labels:
            return {}

        try:
            labels = json.loads(self.labels)
            return labels if isinstance(labels, dict) else {}
        except json.JSONDecodeError:
            return {}

    def set_labels(self, labels: dict[str, str]) -> None:
        """Set container labels from dictionary"""
        import json

        self.labels = json.dumps(labels, sort_keys=True)
        self.update_timestamp()

    def get_environment(self) -> dict[str, str]:
        """Get container environment as dictionary"""
        import json

        if not self.environment:
            return {}

        try:
            env = json.loads(self.environment)
            return env if isinstance(env, dict) else {}
        except json.JSONDecodeError:
            return {}

    def set_environment(self, env: dict[str, str]) -> None:
        """Set environment variables from dictionary"""
        import json

        self.environment = json.dumps(env, sort_keys=True)
        self.update_timestamp()

    def get_ports(self) -> list[dict[str, Any]]:
        """Get container ports as list"""
        import json

        if not self.ports:
            return []

        try:
            ports = json.loads(self.ports)
            return ports if isinstance(ports, list) else []
        except json.JSONDecodeError:
            return []

    def set_ports(self, ports: list[dict[str, Any]]) -> None:
        """Set port mappings from list"""
        import json

        self.ports = json.dumps(ports, sort_keys=True)
        self.update_timestamp()

    def get_volumes(self) -> list[dict[str, Any]]:
        """Get container volumes as list"""
        import json

        if not self.volumes:
            return []

        try:
            volumes = json.loads(self.volumes)
            return volumes if isinstance(volumes, list) else []
        except json.JSONDecodeError:
            return []

    def set_volumes(self, volumes: list[dict[str, Any]]) -> None:
        """Set volume mounts from list"""
        import json

        self.volumes = json.dumps(volumes, sort_keys=True)
        self.update_timestamp()

    def get_networks(self) -> list[str]:
        """Get container networks as list"""
        import json

        if not self.networks:
            return []

        try:
            networks = json.loads(self.networks)
            return networks if isinstance(networks, list) else []
        except json.JSONDecodeError:
            return []

    def set_networks(self, networks: list[str]) -> None:
        """Set network connections from list"""
        import json

        self.networks = json.dumps(networks, sort_keys=True)
        self.update_timestamp()

    def get_container_spec(self) -> dict[str, Any]:
        """Get container specification as dictionary"""
        import json

        try:
            return json.loads(self.container_spec or "{}")
        except json.JSONDecodeError:
            return {}

    def set_container_spec(self, spec: dict[str, Any]) -> None:
        """Set container specification from dictionary"""
        import json

        self.container_spec = json.dumps(spec, sort_keys=True)
        self.update_timestamp()

    def is_excluded_from_updates(self) -> bool:
        """Check if container should be excluded from updates"""
        labels = self.get_labels()

        # Check harbor.exclude label
        if labels.get("harbor.exclude", "").lower() in ("true", "1", "yes"):
            return True

        # Check harbor.enable label (if false, exclude)
        if labels.get("harbor.enable", "").lower() in ("false", "0", "no"):
            return True

        # Check for Harbor self-exclusion
        if "harbor" in self.docker_name.lower():
            return True

        return False

    def is_running(self) -> bool:
        """Check if container is running"""
        return self.status == "running"

    def is_stopped(self) -> bool:
        """Check if container is stopped"""
        return self.status in ("stopped", "exited")

    def should_be_running(self) -> bool:
        """Check if container should be running based on desired state"""
        return self.desired_state == "running"

    def get_image_name_tag(self) -> tuple[str, str]:
        """Get image name and tag as tuple"""
        return (self.image_repo, self.image_tag)

    def get_update_summary(self) -> dict[str, Any]:
        """Get update statistics summary"""
        return {
            "update_count": self.update_count,
            "last_update_success": self.last_update_success,
            "last_update_duration_ms": self.last_update_duration_ms,
            "last_updated_at": self.last_updated_at.isoformat()
            if self.last_updated_at
            else None,
        }

    def to_dict(self, include_timestamps: bool = True) -> dict[str, Any]:
        """Convert container to dictionary - matching parent signature"""
        base_dict = super().to_dict(include_timestamps=include_timestamps)

        # Ensure we have a dictionary
        result: dict[str, Any] = base_dict if isinstance(base_dict, dict) else {}

        # Parse JSON fields
        result["labels"] = self.get_labels()
        result["environment"] = self.get_environment()
        result["ports"] = self.get_ports()
        result["volumes"] = self.get_volumes()
        result["networks"] = self.get_networks()

        return result

    def to_summary_dict(self) -> dict[str, Any]:
        """Get container summary for API responses"""
        return {
            "uid": self.uid,
            "docker_id": self.docker_id,
            "docker_name": self.docker_name,
            "image_ref": self.image_ref,
            "current_digest": self.current_digest[:12] + "..."
            if self.current_digest
            else None,
            "status": self.status,
            "managed": self.managed,
            "auto_discovered": self.auto_discovered,
            "is_excluded": self.is_excluded_from_updates(),
            "last_seen_at": self.last_seen_at.isoformat(),
            "update_count": self.update_count,
        }
