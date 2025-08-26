# app/db/base.py
"""
Harbor Database Base Classes

Base model classes and mixins for Harbor database models.
Provides common functionality for timestamps, soft deletes, and auditing.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """
    Base class for all database models.

    Uses SQLAlchemy 2.0 declarative base.
    """

    pass


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at timestamps.

    Automatically manages timestamp fields for record creation
    and updates.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        doc="Record creation timestamp",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=func.now(),
        doc="Record last update timestamp",
    )

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time."""
        self.updated_at = datetime.now(UTC)


class SoftDeleteMixin:
    """
    Mixin for soft delete functionality.

    Records are marked as deleted instead of being removed
    from the database.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        doc="Soft delete timestamp",
    )

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        doc="Soft delete flag",
    )

    def soft_delete(self) -> None:
        """Mark record as deleted."""
        self.deleted_at = datetime.now(UTC)
        self.is_deleted = True

    def restore(self) -> None:
        """Restore a soft-deleted record."""
        self.deleted_at = None
        self.is_deleted = False

    @property
    def is_active(self) -> bool:
        """Check if record is active (not deleted)."""
        return not self.is_deleted


class UUIDMixin:
    """
    Mixin that adds a UUID field for stable identification.

    Useful for external references that shouldn't change even
    if the primary key does.
    """

    uid: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        unique=True,
        default=lambda: str(uuid.uuid4()),
        doc="UUID for stable external reference",
    )


class AuditMixin:
    """
    Mixin for audit fields.

    Tracks who created and last modified a record.
    Note: User tracking will be fully implemented when multi-user
    support is added (currently behind feature flag).
    """

    @declared_attr
    def created_by_id(cls) -> Mapped[int | None]:
        """ID of user who created the record."""
        return mapped_column(
            Integer,
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            doc="User who created this record",
        )

    @declared_attr
    def updated_by_id(cls) -> Mapped[int | None]:
        """ID of user who last updated the record."""
        return mapped_column(
            Integer,
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            doc="User who last updated this record",
        )

    notes: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="Audit notes or comments"
    )


class BaseModel(Base, TimestampMixin):
    """
    Base model with common functionality for all Harbor models.

    Provides:
    - Automatic ID primary key
    - Automatic timestamps (created_at, updated_at)
    - Dictionary conversion
    - String representation
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, doc="Primary key"
    )

    def to_dict(self, **kwargs: Any) -> dict[str, Any]:
        """
        Convert model instance to dictionary.

        Args:
            **kwargs: Additional options for subclasses
                - exclude: Set of column names to exclude
                - include_timestamps: Whether to include timestamps (default: True)
                - include_sensitive: Whether to include sensitive data (default: False)

        Returns:
            Dictionary representation of the model
        """
        exclude = set(kwargs.get("exclude", set()))
        include_timestamps = kwargs.get("include_timestamps", True)

        result: dict[str, Any] = {}

        # Get all mapped columns
        if hasattr(self, "__table__"):
            for column in self.__table__.columns:
                if column.name not in exclude:
                    # Skip timestamps if requested
                    if not include_timestamps and column.name in (
                        "created_at",
                        "updated_at",
                    ):
                        continue

                    value = getattr(self, column.name)

                    # Convert datetime to ISO format
                    if isinstance(value, datetime):
                        result[column.name] = value.isoformat()
                    else:
                        result[column.name] = value

        return result

    def update_from_dict(
        self, data: dict[str, Any], exclude: set[str] | None = None
    ) -> None:
        """
        Update model instance from dictionary.

        Args:
            data: Dictionary of values to update
            exclude: Set of column names to exclude from updates
        """
        exclude = exclude or {"id", "created_at", "updated_at", "uid"}

        for key, value in data.items():
            if key not in exclude and hasattr(self, key):
                setattr(self, key, value)

    def __repr__(self) -> str:
        """String representation of the model."""
        class_name = self.__class__.__name__

        # Try to use meaningful identifiers
        if hasattr(self, "name"):
            identifier = f"name='{self.name}'"
        elif hasattr(self, "username"):
            identifier = f"username='{self.username}'"
        elif hasattr(self, "uid"):
            identifier = f"uid='{self.uid}'"
        else:
            identifier = f"id={self.id}"

        return f"<{class_name}({identifier})>"


class SingletonModel(Base, TimestampMixin):
    """
    Base class for singleton models (like SystemSettings).

    Ensures only one record can exist with id=1.
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, default=1, doc="Singleton ID (always 1)"
    )

    __table_args__ = (CheckConstraint("id = 1", name="check_singleton_id"),)

    def to_dict(self, **kwargs: Any) -> dict[str, Any]:
        """
        Convert singleton model instance to dictionary.

        Args:
            **kwargs: Additional options for subclasses

        Returns:
            Dictionary representation of the model
        """
        exclude = kwargs.get("exclude", set())
        include_timestamps = kwargs.get("include_timestamps", True)

        result: dict[str, Any] = {}

        # Get all mapped columns
        if hasattr(self, "__table__"):
            for column in self.__table__.columns:
                if column.name not in exclude:
                    # Skip timestamps if requested
                    if not include_timestamps and column.name in (
                        "created_at",
                        "updated_at",
                    ):
                        continue

                    value = getattr(self, column.name)

                    # Convert datetime to ISO format
                    if isinstance(value, datetime):
                        result[column.name] = value.isoformat()
                    else:
                        result[column.name] = value

        return result

    def __repr__(self) -> str:
        """String representation of singleton model."""
        return f"<{self.__class__.__name__}(singleton)>"


class NamedModel(BaseModel):
    """
    Base model for entities with a name field.

    Provides common name field and name-based operations.
    """

    __abstract__ = True

    name: Mapped[str] = mapped_column(String(100), nullable=False, doc="Entity name")

    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="Entity description"
    )

    def __repr__(self) -> str:
        """String representation using name."""
        return f"<{self.__class__.__name__}(name='{self.name}')>"


# Import all models to ensure they're registered with Base.metadata
# This is important for Alembic migrations to detect all tables
def import_all_models():
    """Import all models to register them with SQLAlchemy metadata."""
    try:
        # Import all model modules here as they're created
        from app.db.models import (
            api_key,
            audit,
            container,
            job,
            policy,
            registry,
            settings,
            user,
        )

        logger.debug("All database models imported successfully")
    except ImportError as e:
        # It's OK if not all models exist yet during initial development
        logger.debug(f"Some models not yet created: {e}")


# Try to import models but don't fail if they don't exist yet
from app.utils.logging import get_logger


logger = get_logger(__name__)

try:
    import_all_models()
except Exception as e:
    logger.debug(f"Models import during module load: {e}")

__all__ = [
    "AuditMixin",
    "Base",
    "BaseModel",
    "NamedModel",
    "SingletonModel",
    "SoftDeleteMixin",
    "TimestampMixin",
    "UUIDMixin",
    "import_all_models",
]
