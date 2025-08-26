# app/db/base.py
"""
Harbor Database Base Classes - FIXED TYPE ANNOTATIONS

Base model classes and mixins for Harbor database models with proper typing.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models"""

    pass


class MetadataMixin:
    """Mixin for basic metadata columns with proper typing"""

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, doc="Primary key"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        doc="Record creation timestamp",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        doc="Record last update timestamp",
    )


class TimestampMixin(MetadataMixin):
    """Mixin that provides timestamp functionality with proper typing"""

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp"""
        self.updated_at = datetime.now(UTC)

    def to_dict(self, include_timestamps: bool = True) -> dict[str, Any]:
        """
        Convert model to dictionary with proper typing

        Args:
            include_timestamps: Whether to include timestamp fields

        Returns:
            Dictionary representation of the model
        """
        result: dict[str, Any] = {}

        # Get all mapped columns using SQLAlchemy inspection
        # This is the proper way to get column information
        if hasattr(self, "__table__"):
            for column in self.__table__.columns:
                value = getattr(self, column.name)

                # Skip timestamps if not requested
                if not include_timestamps and column.name in (
                    "created_at",
                    "updated_at",
                ):
                    continue

                # Convert datetime to ISO format
                if isinstance(value, datetime):
                    result[column.name] = value.isoformat()
                else:
                    result[column.name] = value

        return result


class BaseModel(Base, TimestampMixin):
    """Base model class for all Harbor models"""

    __abstract__ = True

    def __repr__(self) -> str:
        """String representation of the model"""
        class_name = self.__class__.__name__
        if hasattr(self, "id"):
            return f"<{class_name}(id={self.id})>"
        else:
            return f"<{class_name}()>"


class SingletonModel(BaseModel):
    """
    Base class for singleton models (like SystemSettings)
    Ensures only one record can exist with id=1
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, default=1, doc="Singleton ID (always 1)"
    )

    __table_args__ = (CheckConstraint("id = 1", name="check_singleton_id"),)
