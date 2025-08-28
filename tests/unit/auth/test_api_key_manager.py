# tests/unit/auth/test_api_key_manager.py
"""
Unit tests for API Key Manager
"""

import pytest
from unittest.mock import patch

from app.auth.api_keys import APIKeyManager


class TestAPIKeyManager:
    """Test APIKeyManager functionality"""

    def test_generate_api_key(self, api_key_manager):
        """Test API key generation"""
        plain_key, hashed_key = api_key_manager.generate_api_key()

        assert plain_key.startswith("sk_harbor_")
        assert len(plain_key) > 40
        assert len(hashed_key) == 64  # SHA256 hex digest
        assert plain_key != hashed_key

    def test_validate_api_key_format(self, api_key_manager):
        """Test API key format validation"""
        # Valid keys - need at least 32 chars after prefix
        assert api_key_manager.validate_api_key_format(
            "sk_harbor_abcdefghijklmnopqrstuvwxyz0123456789"  # pragma: allowlist secret
        )
        assert api_key_manager.validate_api_key_format(
            "sk_harbor_12345678901234567890123456789012"  # pragma: allowlist secret
        )

        # Invalid keys
        assert not api_key_manager.validate_api_key_format("")
        assert not api_key_manager.validate_api_key_format("wrong_prefix")
        assert not api_key_manager.validate_api_key_format("sk_harbor_")
        assert not api_key_manager.validate_api_key_format(
            "sk_harbor_tooshort"
        )  # Less than 32 chars
        assert not api_key_manager.validate_api_key_format(
            "sk_harbor_!@#$%^&*()!@#$%^&*()!@#$%^&*()"  # pragma: allowlist secret
        )  # Invalid chars

    def test_hash_consistency(self, api_key_manager):
        """Test that hashing is consistent"""
        api_key = "sk_harbor_test_key_12345678901234567890"  # pragma: allowlist secret # At least 32 chars after prefix

        hash1 = api_key_manager.hash_api_key(api_key)
        hash2 = api_key_manager.hash_api_key(api_key)

        assert hash1 == hash2

    def test_verify_api_key(self, api_key_manager):
        """Test API key verification"""
        plain_key, hashed_key = api_key_manager.generate_api_key()

        # Correct key should verify
        assert api_key_manager.verify_api_key(plain_key, hashed_key)

        # Wrong key should not verify
        assert not api_key_manager.verify_api_key("wrong_key", hashed_key)
        assert not api_key_manager.verify_api_key(plain_key, "wrong_hash")


@pytest.mark.asyncio
class TestAPIKeyManagerIntegration:
    """Test API Key Manager with database integration"""

    async def test_complete_api_key_lifecycle(
        self, committed_session, sample_user, api_key_manager
    ):
        """Test creating and using an API key"""
        from app.db.models.api_key import APIKey

        # Generate key
        plain_key, hashed_key = api_key_manager.generate_api_key()

        # Store in database
        api_key = APIKey(
            name="lifecycle-test",
            key_hash=hashed_key,
            created_by_user_id=sample_user.id,
        )
        committed_session.add(api_key)
        await committed_session.commit()

        # Verify it can be retrieved and verified
        assert api_key.id is not None
        assert api_key_manager.verify_api_key(plain_key, api_key.key_hash)
