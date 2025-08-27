# tests/unit/auth/test_sessions.py
"""Test session management functionality."""

import pytest
from datetime import datetime, timedelta, UTC
from app.auth.sessions import SessionManager, SessionData


class TestSessionManager:
    """Test SessionManager class."""

    @pytest.fixture
    def session_manager(self):
        """Create a session manager instance."""
        return SessionManager()

    def test_create_session(self, session_manager):
        """Test session creation."""
        session = session_manager.create_session(
            user_id=1,
            username="testuser",
            is_admin=False,
            ip_address="127.0.0.1",
            user_agent="TestBrowser/1.0",
        )

        assert session.session_id is not None
        assert len(session.session_id) > 20
        assert session.user_id == 1
        assert session.username == "testuser"
        assert session.csrf_token is not None
        assert session.expires_at > datetime.now(UTC)

    def test_get_valid_session(self, session_manager):
        """Test retrieving a valid session."""
        created = session_manager.create_session(user_id=1, username="testuser")

        retrieved = session_manager.get_session(created.session_id)
        assert retrieved is not None
        assert retrieved.user_id == 1
        assert retrieved.username == "testuser"

    def test_get_expired_session(self, session_manager):
        """Test retrieving an expired session."""
        session = session_manager.create_session(user_id=1, username="testuser")

        # Manually expire the session
        session.expires_at = datetime.now(UTC) - timedelta(hours=1)

        retrieved = session_manager.get_session(session.session_id)
        assert retrieved is None

    def test_invalidate_session(self, session_manager):
        """Test session invalidation."""
        session = session_manager.create_session(user_id=1, username="testuser")

        assert session_manager.invalidate_session(session.session_id) is True
        assert session_manager.get_session(session.session_id) is None

    def test_csrf_token_validation(self, session_manager):
        """Test CSRF token validation."""
        session = session_manager.create_session(user_id=1, username="testuser")

        assert (
            session_manager.validate_csrf_token(session.session_id, session.csrf_token)
            is True
        )

        assert (
            session_manager.validate_csrf_token(session.session_id, "invalid_token")
            is False
        )
