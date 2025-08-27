# tests/integration/test_auth_integration.py
"""Integration tests for authentication system."""

import pytest
from sqlalchemy import select
from app.auth.manager import get_auth_manager
from app.auth.password import hash_password
from app.db.models.user import User
from app.db.models.api_key import APIKey


@pytest.mark.database
class TestAuthenticationIntegration:
    """Test authentication integration with database."""

    @pytest.fixture
    async def test_user(
        self, committed_session
    ):  # Changed from async_session to committed_session
        """Create a test user."""
        user = User(
            username="authtest",
            password_hash=hash_password("TestPass123!"),
            email="auth@test.com",
            display_name="Auth Test User",
            is_admin=False,
            is_active=True,
        )
        committed_session.add(user)
        await committed_session.commit()
        # No need to refresh - the session is still open
        return user

    async def test_authenticate_user_success(
        self, committed_session, test_user
    ):  # Changed parameter
        """Test successful user authentication."""
        auth_manager = get_auth_manager()

        result = await auth_manager.authenticate_user(
            db=committed_session,  # Changed from async_session
            username="authtest",
            password="TestPass123!",  # pragma: allowlist secret
            ip_address="127.0.0.1",
        )

        assert result.success is True
        assert result.user is not None
        assert result.user.username == "authtest"
        assert result.session is not None
        assert result.error_message is None

    async def test_authenticate_user_wrong_password(
        self, committed_session, test_user
    ):  # Changed parameter
        """Test authentication with wrong password."""
        auth_manager = get_auth_manager()

        result = await auth_manager.authenticate_user(
            db=committed_session,  # Changed from async_session
            username="authtest",
            password="WrongPassword",  # pragma: allowlist secret
            ip_address="127.0.0.1",
        )

        assert result.success is False
        assert result.user is None
        assert result.session is None
        assert "Invalid username or password" in result.error_message

    async def test_account_lockout(
        self, committed_session, test_user
    ):  # Changed parameter
        """Test account lockout after failed attempts."""
        auth_manager = get_auth_manager()

        # Make multiple failed attempts
        for _ in range(6):
            await auth_manager.authenticate_user(
                db=committed_session,  # Changed from async_session
                username="authtest",
                password="WrongPassword",  # pragma: allowlist secret
                ip_address="127.0.0.1",
            )

        # Next attempt should be locked
        result = await auth_manager.authenticate_user(
            db=committed_session,  # Changed from async_session
            username="authtest",
            password="TestPass123!",  # pragma: allowlist secret
            ip_address="127.0.0.1",
        )

        assert result.success is False
        assert result.account_locked is True
        assert "locked" in result.error_message.lower()
