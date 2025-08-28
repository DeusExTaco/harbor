# tests/unit/auth/test_api_key_integration.py
"""
Integration tests for API key with authentication manager.
"""

import pytest
from datetime import datetime, timedelta, UTC

from app.auth.manager import AuthenticationManager
from app.auth.api_keys import APIKeyManager
from app.db.models.user import User
from app.db.models.api_key import APIKey


@pytest.mark.asyncio
async def test_api_key_authentication_flow(committed_session, test_user):
    """Test complete API key authentication flow."""
    auth_manager = AuthenticationManager()
    api_key_manager = APIKeyManager()

    # Ensure auth_manager uses same api_key_manager for consistent HMAC
    auth_manager.api_key_manager = api_key_manager

    # Generate API key
    plain_key, hashed_key = api_key_manager.generate_api_key()

    # Create API key in database
    api_key_record = APIKey(
        name="test-key",
        key_hash=hashed_key,
        created_by_user_id=test_user.id,
    )
    committed_session.add(api_key_record)
    await committed_session.commit()

    # Test authentication
    result = await auth_manager.authenticate_api_key(
        committed_session, plain_key, ip_address="127.0.0.1"
    )

    assert result.success is True
    assert result.user.id == test_user.id
    assert result.api_key.id == api_key_record.id

    # Verify usage was tracked
    await committed_session.refresh(api_key_record)
    assert api_key_record.usage_count == 1
    assert api_key_record.last_used_ip == "127.0.0.1"


@pytest.mark.asyncio
async def test_expired_api_key_rejection(committed_session, test_user):
    """Test that expired API keys are rejected."""
    auth_manager = AuthenticationManager()
    api_key_manager = APIKeyManager()

    # Ensure auth_manager uses same api_key_manager for consistent HMAC
    auth_manager.api_key_manager = api_key_manager

    plain_key, hashed_key = api_key_manager.generate_api_key()

    # Create expired API key
    api_key_record = APIKey(
        name="expired-key",
        key_hash=hashed_key,
        created_by_user_id=test_user.id,
        expires_at=datetime.now(UTC) - timedelta(days=1),  # Expired
    )
    committed_session.add(api_key_record)
    await committed_session.commit()

    # Test authentication
    result = await auth_manager.authenticate_api_key(
        committed_session, plain_key, ip_address="127.0.0.1"
    )

    assert result.success is False
    assert result.error_message == "API key has expired"


@pytest.mark.asyncio
async def test_revoked_api_key_rejection(committed_session, test_user):
    """Test that revoked API keys are rejected."""
    auth_manager = AuthenticationManager()
    api_key_manager = APIKeyManager()

    # Ensure auth_manager uses same api_key_manager for consistent HMAC
    auth_manager.api_key_manager = api_key_manager

    plain_key, hashed_key = api_key_manager.generate_api_key()

    # Create and revoke API key
    api_key_record = APIKey(
        name="revoked-key",
        key_hash=hashed_key,
        created_by_user_id=test_user.id,
    )
    api_key_record.revoke()
    committed_session.add(api_key_record)
    await committed_session.commit()

    # Test authentication
    result = await auth_manager.authenticate_api_key(
        committed_session, plain_key, ip_address="127.0.0.1"
    )

    assert result.success is False
    assert result.error_message == "Invalid API key"
