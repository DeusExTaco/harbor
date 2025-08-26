# app/db/models/job.py
"""
Harbor Job Model

Job execution tracking and management.
TODO: Full implementation in M2 milestone.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel


class Job(BaseModel):
    """Job model for tracking async operations"""

    __tablename__ = "jobs"

    # Job identification
    job_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
        index=True,
        doc="UUID for job tracking",
    )

    job_type: Mapped[str] = mapped_column(String(50), nullable=False, doc="Type of job")

    job_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, doc="Human readable job name"
    )

    # Target information
    container_uid: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("containers.uid", ondelete="SET NULL"),
        nullable=True,
        doc="Target container if applicable",
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
        doc="Job status",
    )

    # Timing
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        doc="Job creation time",
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, doc="Job start time"
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, doc="Job completion time"
    )

    # Results
    result_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="Result message"
    )

    result_data: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="JSON result data"
    )

    # Trigger information
    triggered_by: Mapped[str] = mapped_column(
        String(20), nullable=False, doc="scheduler, manual, api, webhook"
    )

    def __repr__(self) -> str:
        return f"<Job(id={self.id}, job_id='{self.job_id}', type='{self.job_type}', status='{self.status}')>"
