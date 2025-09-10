# tests/integration/middleware/test_audit_logging_real_integration.py
"""
Integration tests for the ACTUAL audit logging implementation.

Tests the real app/db/models/audit.py code with a test database.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta, UTC
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

# Import the ACTUAL audit model and related components
from app.db.models.audit import AuditLog
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, and_, or_
import tempfile

# Import base model for database setup
from app.db.base import BaseModel


class TestRealAuditLogModel:
    """Test the actual AuditLog model implementation."""

    @pytest.fixture
    async def test_engine(self):
        """Create a test database engine."""
        # Create a temporary SQLite database for testing
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_file = tmp_file.name

        # Create async engine
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{db_file}", echo=False, future=True
        )

        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(BaseModel.metadata.create_all)

        yield engine

        # Cleanup
        await engine.dispose()
        os.unlink(db_file)

    @pytest.fixture
    async def db_session(self, test_engine):
        """Create a test database session."""
        async_session = async_sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )

        async with async_session() as session:
            yield session
            await session.rollback()

    def test_audit_log_model_import(self):
        """Test that the AuditLog model imports correctly."""
        assert AuditLog is not None
        assert hasattr(AuditLog, "__tablename__")
        assert AuditLog.__tablename__ == "audit_logs"

    @pytest.mark.asyncio
    async def test_create_audit_log(self, db_session):
        """Test creating an audit log entry."""
        audit_log = AuditLog(
            event_id="test_event_001",
            actor_type="user",
            actor_id="1",
            actor_name="testuser",
            action="test_action",
            resource_type="test_resource",
            resource_id="1",
            success=True,
            error_message=None,
            event_metadata=json.dumps({"test": "data"}),
        )

        db_session.add(audit_log)
        await db_session.commit()

        # Verify the log was created with auto-generated fields
        assert audit_log.id is not None
        assert audit_log.timestamp is not None
        assert isinstance(audit_log.timestamp, datetime)
        assert audit_log.event_id == "test_event_001"

    @pytest.mark.asyncio
    async def test_audit_log_defaults(self, db_session):
        """Test default values in audit log."""
        audit_log = AuditLog(
            event_id="test_event_002",
            actor_type="system",
            actor_id="scheduler",
            action="automated_check",
            resource_type="container",
            success=True,
        )

        db_session.add(audit_log)
        await db_session.commit()

        # Check defaults
        assert audit_log.actor_name is None
        assert audit_log.resource_id is None
        assert audit_log.error_message is None
        assert audit_log.event_metadata == "{}"  # Default empty JSON
        assert audit_log.timestamp.tzinfo is not None  # Should be timezone-aware

    @pytest.mark.asyncio
    async def test_failed_action_audit(self, db_session):
        """Test logging a failed action."""
        audit_log = AuditLog(
            event_id="test_event_003",
            actor_type="user",
            actor_id="2",
            actor_name="failuser",
            action="unauthorized_access",
            resource_type="admin_panel",
            resource_id="admin",
            success=False,
            error_message="Access denied: insufficient permissions",
        )

        db_session.add(audit_log)
        await db_session.commit()

        assert audit_log.success is False
        assert "Access denied" in audit_log.error_message

    @pytest.mark.asyncio
    async def test_query_audit_logs_by_actor(self, db_session):
        """Test querying audit logs by actor."""
        # Create multiple logs
        for i in range(5):
            log = AuditLog(
                event_id=f"query_test_{i}",
                actor_type="user",
                actor_id=str(i % 2),  # Alternating between "0" and "1"
                action="test_action",
                resource_type="test",
                success=True,
            )
            db_session.add(log)

        await db_session.commit()

        # Query for actor_id="0"
        stmt = select(AuditLog).where(AuditLog.actor_id == "0")
        result = await db_session.execute(stmt)
        logs = result.scalars().all()

        assert len(logs) >= 2
        assert all(log.actor_id == "0" for log in logs)

    @pytest.mark.asyncio
    async def test_query_audit_logs_by_time_range(self, db_session):
        """Test querying audit logs by time range."""
        now = datetime.now(UTC)

        # Create logs at different times
        old_log = AuditLog(
            event_id="old_event",
            timestamp=now - timedelta(days=10),
            actor_type="system",
            actor_id="scheduler",
            action="old_action",
            resource_type="test",
            success=True,
        )

        recent_log = AuditLog(
            event_id="recent_event",
            timestamp=now - timedelta(hours=1),
            actor_type="system",
            actor_id="scheduler",
            action="recent_action",
            resource_type="test",
            success=True,
        )

        db_session.add_all([old_log, recent_log])
        await db_session.commit()

        # Query last 24 hours
        cutoff = now - timedelta(days=1)
        stmt = select(AuditLog).where(AuditLog.timestamp >= cutoff)
        result = await db_session.execute(stmt)
        logs = result.scalars().all()

        # Should only get the recent log
        assert len(logs) >= 1
        assert all(log.timestamp >= cutoff for log in logs)
        assert "recent_event" in [log.event_id for log in logs]

    @pytest.mark.asyncio
    async def test_query_failed_operations(self, db_session):
        """Test querying for failed operations."""
        # Create mix of successful and failed operations
        for i in range(6):
            log = AuditLog(
                event_id=f"op_{i}",
                actor_type="system",
                actor_id="updater",
                action="update_container",
                resource_type="container",
                resource_id=str(i),
                success=(i % 2 == 0),  # Alternate success/failure
                error_message="Update failed" if i % 2 else None,
            )
            db_session.add(log)

        await db_session.commit()

        # Query failed operations
        stmt = select(AuditLog).where(AuditLog.success == False)
        result = await db_session.execute(stmt)
        failed_logs = result.scalars().all()

        assert len(failed_logs) >= 3
        assert all(not log.success for log in failed_logs)
        assert all(log.error_message is not None for log in failed_logs)

    @pytest.mark.asyncio
    async def test_audit_log_with_metadata(self, db_session):
        """Test storing JSON metadata in audit logs."""
        metadata = {
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0",
            "session_id": "sess_123",
            "additional_info": {"nested": "data", "count": 42},
        }

        audit_log = AuditLog(
            event_id="metadata_test",
            actor_type="user",
            actor_id="3",
            action="complex_action",
            resource_type="api",
            resource_id="endpoint_1",
            success=True,
            event_metadata=json.dumps(metadata),
        )

        db_session.add(audit_log)
        await db_session.commit()

        # Retrieve and verify
        stmt = select(AuditLog).where(AuditLog.event_id == "metadata_test")
        result = await db_session.execute(stmt)
        log = result.scalar_one()

        # Parse the metadata
        stored_metadata = json.loads(log.event_metadata)
        assert stored_metadata["ip_address"] == "192.168.1.100"
        assert stored_metadata["additional_info"]["count"] == 42

    @pytest.mark.asyncio
    async def test_audit_log_repr(self, db_session):
        """Test the string representation of audit logs."""
        audit_log = AuditLog(
            event_id="repr_test",
            actor_type="user",
            actor_id="1",
            action="test_repr",
            resource_type="test",
            success=True,
        )

        db_session.add(audit_log)
        await db_session.commit()

        repr_str = repr(audit_log)
        assert "AuditLog" in repr_str
        assert "repr_test" in repr_str
        assert "test_repr" in repr_str


class TestAuditLogIntegrationScenarios:
    """Test real-world audit logging scenarios."""

    @pytest.fixture
    async def test_engine(self):
        """Create a test database engine."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_file = tmp_file.name

        engine = create_async_engine(
            f"sqlite+aiosqlite:///{db_file}", echo=False, future=True
        )

        async with engine.begin() as conn:
            await conn.run_sync(BaseModel.metadata.create_all)

        yield engine

        await engine.dispose()
        os.unlink(db_file)

    @pytest.fixture
    async def db_session(self, test_engine):
        """Create a test database session."""
        async_session = async_sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )

        async with async_session() as session:
            yield session

    @pytest.mark.asyncio
    async def test_authentication_audit_trail(self, db_session):
        """Test creating an authentication audit trail."""
        # Successful login
        login_success = AuditLog(
            event_id="auth_001",
            actor_type="user",
            actor_id="user_123",
            actor_name="john.doe",
            action="user_login",
            resource_type="auth",
            resource_id="session_456",
            success=True,
            event_metadata=json.dumps(
                {"ip_address": "192.168.1.100", "user_agent": "Chrome/120.0"}
            ),
        )

        # Failed login attempt
        login_fail = AuditLog(
            event_id="auth_002",
            actor_type="user",
            actor_id="unknown",
            action="user_login_failed",
            resource_type="auth",
            success=False,
            error_message="Invalid credentials",
            event_metadata=json.dumps(
                {"ip_address": "192.168.1.101", "attempted_username": "admin"}
            ),
        )

        db_session.add_all([login_success, login_fail])
        await db_session.commit()

        # Query authentication events
        stmt = select(AuditLog).where(AuditLog.resource_type == "auth")
        result = await db_session.execute(stmt)
        auth_logs = result.scalars().all()

        assert len(auth_logs) == 2
        assert any(log.success for log in auth_logs)
        assert any(not log.success for log in auth_logs)

    @pytest.mark.asyncio
    async def test_container_update_audit_trail(self, db_session):
        """Test creating a container update audit trail."""
        # Container update initiated
        update_start = AuditLog(
            event_id="update_001",
            actor_type="scheduler",
            actor_id="auto_scheduler",
            action="container_update_started",
            resource_type="container",
            resource_id="nginx_001",
            success=True,
            event_metadata=json.dumps(
                {"from_version": "1.21.0", "to_version": "1.22.0"}
            ),
        )

        # Container update completed
        update_complete = AuditLog(
            event_id="update_002",
            actor_type="scheduler",
            actor_id="auto_scheduler",
            action="container_update_completed",
            resource_type="container",
            resource_id="nginx_001",
            success=True,
            event_metadata=json.dumps({"duration_ms": 45000, "new_version": "1.22.0"}),
        )

        db_session.add_all([update_start, update_complete])
        await db_session.commit()

        # Query container update events
        stmt = (
            select(AuditLog)
            .where(
                and_(
                    AuditLog.resource_type == "container",
                    AuditLog.resource_id == "nginx_001",
                )
            )
            .order_by(AuditLog.timestamp)
        )

        result = await db_session.execute(stmt)
        update_logs = result.scalars().all()

        assert len(update_logs) == 2
        assert update_logs[0].action == "container_update_started"
        assert update_logs[1].action == "container_update_completed"

    @pytest.mark.asyncio
    async def test_security_event_correlation(self, db_session):
        """Test correlating security events from the same IP."""
        ip_address = "192.168.1.50"

        # Create multiple failed login attempts from same IP
        for i in range(5):
            failed_attempt = AuditLog(
                event_id=f"security_{i}",
                actor_type="user",
                actor_id="unknown",
                action="user_login_failed",
                resource_type="auth",
                success=False,
                error_message="Invalid credentials",
                event_metadata=json.dumps(
                    {"ip_address": ip_address, "attempt_number": i + 1}
                ),
            )
            db_session.add(failed_attempt)

        await db_session.commit()

        # Query all failed attempts
        stmt = select(AuditLog).where(
            and_(AuditLog.action == "user_login_failed", AuditLog.success == False)
        )
        result = await db_session.execute(stmt)
        failed_attempts = result.scalars().all()

        # Check that we can identify the pattern
        assert len(failed_attempts) >= 5

        # In a real system, this would trigger security measures
        metadata_list = [json.loads(log.event_metadata) for log in failed_attempts]
        same_ip_attempts = [
            m for m in metadata_list if m.get("ip_address") == ip_address
        ]
        assert len(same_ip_attempts) == 5


class TestAuditLogValidation:
    """Test audit log validation and constraints."""

    @pytest.fixture
    async def test_engine(self):
        """Create a test database engine."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_file = tmp_file.name

        engine = create_async_engine(
            f"sqlite+aiosqlite:///{db_file}", echo=False, future=True
        )

        async with engine.begin() as conn:
            await conn.run_sync(BaseModel.metadata.create_all)

        yield engine

        await engine.dispose()
        os.unlink(db_file)

    @pytest.fixture
    async def db_session(self, test_engine):
        """Create a test database session."""
        async_session = async_sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )

        async with async_session() as session:
            yield session

    @pytest.mark.asyncio
    async def test_required_fields(self, db_session):
        """Test that required fields must be provided."""
        # This should work - all required fields provided
        valid_log = AuditLog(
            event_id="required_test",
            actor_type="user",
            actor_id="1",
            action="test_action",
            resource_type="test",
            success=True,
        )

        db_session.add(valid_log)
        await db_session.commit()

        assert valid_log.id is not None

    @pytest.mark.asyncio
    async def test_actor_types(self, db_session):
        """Test different actor types."""
        actor_types = ["user", "api_key", "system", "scheduler"]

        for actor_type in actor_types:
            log = AuditLog(
                event_id=f"actor_{actor_type}",
                actor_type=actor_type,
                actor_id=f"{actor_type}_id",
                action=f"{actor_type}_action",
                resource_type="test",
                success=True,
            )
            db_session.add(log)

        await db_session.commit()

        # Query and verify all actor types
        stmt = select(AuditLog.actor_type).distinct()
        result = await db_session.execute(stmt)
        stored_types = result.scalars().all()

        for actor_type in actor_types:
            assert actor_type in stored_types
