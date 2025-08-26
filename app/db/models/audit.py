# app/db/models/audit.py
"""
Harbor Audit Log Model

Comprehensive audit trail for all operations.
TODO: Full implementation in M1 milestone.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel


class AuditLog(BaseModel):
    """Audit log model for tracking all system operations"""

    __tablename__ = "audit_logs"

    # Event identification
    event_id: Mapped[str] = mapped_column(
        String(36), nullable=False, doc="UUID for event correlation"
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        doc="Event timestamp",
    )

    # Actor information
    actor_type: Mapped[str] = mapped_column(
        String(20), nullable=False, doc="user, api_key, system, scheduler"
    )

    actor_id: Mapped[str] = mapped_column(
        String(100), nullable=False, doc="Actor identifier"
    )

    actor_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, doc="Human readable actor name"
    )

    # Action details
    action: Mapped[str] = mapped_column(
        String(50), nullable=False, doc="Action performed"
    )

    resource_type: Mapped[str] = mapped_column(
        String(50), nullable=False, doc="Resource type affected"
    )

    resource_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, doc="Resource identifier"
    )

    # Result
    success: Mapped[bool] = mapped_column(
        Boolean, nullable=False, doc="Whether action succeeded"
    )

    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="Error message if failed"
    )

    # Additional data - RENAMED from 'metadata' to 'event_metadata'
    event_metadata: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
        server_default="{}",
        doc="JSON metadata for the event",
        name="metadata",  # Keep the database column name as 'metadata'
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, event='{self.event_id}', action='{self.action}')>"
        )
