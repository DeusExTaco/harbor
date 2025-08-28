# tests/unit/auth/test_api_keys.py
"""
Tests for Harbor API Key Management
"""

import pytest
from unittest.mock import Mock, patch

from app.auth.api_keys import APIKeyManager, generate_api_key, hash_api_key


class TestAPIKeyManager:
    """Test API key manager functionality."""

    @pytest.fixture
    def api_key_manager(self):
        """Create API key manager instance."""
        with patch("app.auth.api_keys.get_settings") as mock_settings:
            mock_settings.return_value = Mock()
            manager = APIKeyManager()
            # Use a test HMAC key
            manager._hmac_key = b"test_hmac_key_for_testing_only"
            return manager

    def test_generate_api_key(self, api_key_manager):
        """Test API key generation."""
        plain_key, hashed_key = api_key_manager.generate_api_key()

        # Check format
        assert plain_key.startswith("sk_harbor_")
        assert len(plain_key) > 40  # Prefix + random part

        # Check hash
        assert hashed_key != plain_key
        assert len(hashed_key) == 64  # SHA256 hex digest

    def test_validate_api_key_format(self, api_key_manager):
        """Test API key format validation."""
        # Valid key
        valid_key = "sk_harbor_abcdefghijklmnopqrstuvwxyz0123456789-_"  # pragma: allowlist secret
        assert api_key_manager.validate_api_key_format(valid_key) is True

        # Invalid keys
        assert api_key_manager.validate_api_key_format("") is False
        assert api_key_manager.validate_api_key_format("wrong_prefix") is False
        assert api_key_manager.validate_api_key_format("sk_harbor_") is False
        assert api_key_manager.validate_api_key_format("sk_harbor_invalid!@#") is False

    def test_hash_api_key(self, api_key_manager):
        """Test API key hashing."""
        api_key = "sk_harbor_test_key_123"  # pragma: allowlist secret
        hash1 = api_key_manager.hash_api_key(api_key)
        hash2 = api_key_manager.hash_api_key(api_key)

        # Same key should produce same hash
        assert hash1 == hash2

        # Different key should produce different hash
        different_key = "sk_harbor_different_key_456"
        hash3 = api_key_manager.hash_api_key(different_key)
        assert hash1 != hash3

    def test_verify_api_key(self, api_key_manager):
        """Test API key verification."""
        plain_key, hashed_key = api_key_manager.generate_api_key()

        # Valid verification
        assert api_key_manager.verify_api_key(plain_key, hashed_key) is True

        # Invalid verification
        assert api_key_manager.verify_api_key("wrong_key", hashed_key) is False
        assert api_key_manager.verify_api_key(plain_key, "wrong_hash") is False

    def test_extract_key_hash(self, api_key_manager):
        """Test key hash extraction."""
        plain_key = "sk_harbor_test_key_valid_format"
        key_hash = api_key_manager.extract_key_hash(plain_key)

        assert key_hash is not None
        assert key_hash == api_key_manager.hash_api_key(plain_key)

        # Invalid key should return None
        assert api_key_manager.extract_key_hash("invalid") is None


class TestAPIKeyHelperFunctions:
    """Test module-level helper functions."""

    def test_generate_api_key_function(self):
        """Test generate_api_key helper function."""
        plain_key, hashed_key = generate_api_key()

        assert plain_key.startswith("sk_harbor_")
        assert len(hashed_key) == 64

    def test_hash_api_key_function(self):
        """Test hash_api_key helper function."""
        api_key = "sk_harbor_test_helper_function"  # pragma: allowlist secret
        hashed = hash_api_key(api_key)

        assert len(hashed) == 64
        assert hashed != api_key
