# tests/integration/test_auth_api_keys.py
"""
Integration tests for API key authentication flow
"""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import patch


@pytest.mark.asyncio
@pytest.mark.integration
class TestAPIKeyAuthentication:
    """Test API key authentication integration"""

    async def test_successful_api_key_authentication(
        self, committed_session, sample_user, auth_manager, api_key_manager
    ):
        """Test successful API key authentication"""
        from app.db.models.api_key import APIKey

        # Ensure auth_manager uses the same api_key_manager instance
        # This is the key fix - making sure both use the same HMAC key
        auth_manager.api_key_manager = api_key_manager

        # Create API key
        plain_key, hashed_key = api_key_manager.generate_api_key()
        api_key = APIKey(
            name="auth-test",
            key_hash=hashed_key,
            created_by_user_id=sample_user.id,
        )
        committed_session.add(api_key)
        await committed_session.commit()

        # Authenticate
        result = await auth_manager.authenticate_api_key(
            committed_session, plain_key, ip_address="127.0.0.1"
        )

        assert result.success
        assert result.user.id == sample_user.id
        assert result.api_key.id == api_key.id

        # Check usage was tracked
        await committed_session.refresh(api_key)
        assert api_key.usage_count == 1
        assert api_key.last_used_ip == "127.0.0.1"

    async def test_expired_api_key_rejected(
        self,
        committed_session,
        sample_user,  # Need to use sample_user, not expired_api_key fixture
        auth_manager,
        api_key_manager,
    ):
        """Test that expired API keys are rejected"""
        from app.db.models.api_key import APIKey

        # Ensure auth_manager uses the same api_key_manager instance
        auth_manager.api_key_manager = api_key_manager

        # Create expired API key
        plain_key, hashed_key = api_key_manager.generate_api_key()
        api_key = APIKey(
            name="test-expired-key",
            key_hash=hashed_key,
            created_by_user_id=sample_user.id,
            expires_at=datetime.now(UTC) - timedelta(days=1),  # Expired yesterday
            description="Test expired API key",
        )
        committed_session.add(api_key)
        await committed_session.commit()

        result = await auth_manager.authenticate_api_key(
            committed_session, plain_key, ip_address="127.0.0.1"
        )

        assert not result.success
        assert "expired" in result.error_message.lower()

    async def test_revoked_api_key_rejected(
        self, committed_session, sample_user, auth_manager, api_key_manager
    ):
        """Test that revoked API keys are rejected"""
        from app.db.models.api_key import APIKey

        # Ensure auth_manager uses the same api_key_manager instance
        auth_manager.api_key_manager = api_key_manager

        # Create and revoke API key
        plain_key, hashed_key = api_key_manager.generate_api_key()
        api_key = APIKey(
            name="test-revoked-key",
            key_hash=hashed_key,
            created_by_user_id=sample_user.id,
            description="Test revoked API key",
        )
        api_key.revoke()  # Revoke it immediately
        committed_session.add(api_key)
        await committed_session.commit()

        result = await auth_manager.authenticate_api_key(
            committed_session, plain_key, ip_address="127.0.0.1"
        )

        assert not result.success
        assert result.error_message == "Invalid API key"

    async def test_invalid_format_rejected(self, committed_session, auth_manager):
        """Test that invalid API key formats are rejected"""
        invalid_keys = [
            "",
            "wrong_prefix_key",
            "sk_harbor_",
            "sk_harbor_invalid!@#",
        ]

        for invalid_key in invalid_keys:
            result = await auth_manager.authenticate_api_key(
                committed_session, invalid_key, ip_address="127.0.0.1"
            )

            assert not result.success
            assert result.error_message == "Invalid API key"
