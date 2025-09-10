# tests/integration/middleware/test_csrf_real_integration.py
"""
Integration tests for the ACTUAL CSRF protection implementation.

Tests the real app/auth/csrf.py code, not mocks.
"""

import sys
import os
import pytest
import secrets
from unittest.mock import Mock, patch

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

# Now import the ACTUAL CSRF module - this should fix the coverage issue
import app.auth.csrf
from app.auth.csrf import CSRFProtection, get_csrf_protection


class TestRealCSRFProtection:
    """Test the actual CSRF protection implementation."""

    @pytest.fixture
    def csrf(self):
        """Create a real CSRFProtection instance."""
        return CSRFProtection()

    def test_module_import(self):
        """Test that the module imports correctly."""
        # This ensures the module is actually imported for coverage
        assert app.auth.csrf is not None
        assert hasattr(app.auth.csrf, "CSRFProtection")
        assert hasattr(app.auth.csrf, "get_csrf_protection")

    def test_generate_token(self, csrf):
        """Test actual token generation."""
        token = csrf.generate_token()

        # Verify token properties
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

        # Tokens should be unique
        token2 = csrf.generate_token()
        assert token != token2

    def test_validate_token_success(self, csrf):
        """Test successful token validation."""
        token = "test_token_abc123"

        # Same tokens should validate
        assert csrf.validate_token(token, token) is True

    def test_validate_token_failure(self, csrf):
        """Test failed token validation."""
        token1 = "token_abc123"
        token2 = "token_def456"

        # Different tokens should not validate
        assert csrf.validate_token(token1, token2) is False

    def test_validate_token_empty(self, csrf):
        """Test validation with empty tokens."""
        # Empty tokens should not validate
        assert csrf.validate_token("", "token") is False
        assert csrf.validate_token("token", "") is False
        assert csrf.validate_token("", "") is False
        assert csrf.validate_token(None, "token") is False
        assert csrf.validate_token("token", None) is False

    def test_validate_token_constant_time(self, csrf):
        """Test that validation uses constant-time comparison."""
        # This tests that the actual secrets.compare_digest is used
        token = "test_token_123"

        # Should use constant-time comparison (secrets.compare_digest)
        with patch("secrets.compare_digest") as mock_compare:
            mock_compare.return_value = True
            result = csrf.validate_token(token, token)

            mock_compare.assert_called_once_with(token, token)
            assert result is True

    def test_generate_form_token(self, csrf):
        """Test form token generation."""
        session_token = "session_token_abc123"

        form_token = csrf.generate_form_token(session_token)

        # Currently just returns the session token
        assert form_token == session_token

    def test_token_length_configuration(self):
        """Test that token length is configurable."""
        csrf = CSRFProtection()
        assert csrf.token_length == 32

        # Generate token and check it's appropriately long
        token = csrf.generate_token()
        # URL-safe base64 encoding makes it longer than 32 chars
        assert len(token) >= 32

    def test_get_csrf_protection_singleton(self):
        """Test that get_csrf_protection returns a singleton."""
        # Reset the global instance first
        app.auth.csrf._csrf_protection = None

        csrf1 = get_csrf_protection()
        csrf2 = get_csrf_protection()

        # Should be the same instance
        assert csrf1 is csrf2

        # Should be a CSRFProtection instance
        assert isinstance(csrf1, CSRFProtection)

    def test_logging_on_token_generation(self, csrf):
        """Test that token generation is logged."""
        with patch("app.auth.csrf.logger") as mock_logger:
            token = csrf.generate_token()

            # Should log debug message
            mock_logger.debug.assert_called_with("CSRF token generated")
            assert token is not None

    def test_token_randomness(self, csrf):
        """Test that tokens are cryptographically random."""
        # Generate many tokens and ensure they're all different
        tokens = set()
        for _ in range(100):
            token = csrf.generate_token()
            assert token not in tokens  # Should be unique
            tokens.add(token)

        assert len(tokens) == 100

    def test_token_url_safety(self, csrf):
        """Test that tokens are URL-safe."""
        token = csrf.generate_token()

        # URL-safe characters only
        import string

        url_safe_chars = string.ascii_letters + string.digits + "-_"

        for char in token:
            assert char in url_safe_chars


class TestCSRFMiddlewareIntegration:
    """Test CSRF integration with middleware."""

    @pytest.fixture
    def csrf(self):
        """Get the CSRF protection instance."""
        return get_csrf_protection()

    @pytest.mark.asyncio
    async def test_csrf_token_in_forms(self, csrf):
        """Test that CSRF tokens can be embedded in forms."""
        # Generate a token for a session
        session_token = csrf.generate_token()

        # Generate form token
        form_token = csrf.generate_form_token(session_token)

        # Validate the form token against session token
        is_valid = csrf.validate_token(form_token, session_token)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_csrf_token_rotation(self, csrf):
        """Test token rotation for security."""
        # Generate initial token
        old_token = csrf.generate_token()

        # Generate new token (rotation)
        new_token = csrf.generate_token()

        # Should be different
        assert old_token != new_token

        # Both should be valid tokens on their own
        assert csrf.validate_token(old_token, old_token) is True
        assert csrf.validate_token(new_token, new_token) is True

        # But shouldn't validate against each other
        assert csrf.validate_token(old_token, new_token) is False

    def test_csrf_double_submit_pattern(self, csrf):
        """Test double-submit cookie pattern."""
        # Generate token (would be set as cookie)
        cookie_token = csrf.generate_token()

        # Form/header would submit same token
        submitted_token = cookie_token

        # Should validate
        assert csrf.validate_token(submitted_token, cookie_token) is True

    def test_csrf_attack_prevention(self, csrf):
        """Test that CSRF attacks are prevented."""
        # Legitimate user's token
        legitimate_token = csrf.generate_token()

        # Attacker's forged token
        forged_token = "attacker_forged_token"

        # Forged token should not validate
        assert csrf.validate_token(forged_token, legitimate_token) is False


class TestCSRFEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def csrf(self):
        """Create a CSRF protection instance."""
        return CSRFProtection()

    def test_unicode_tokens(self, csrf):
        """Test handling of unicode in tokens."""
        # The actual implementation uses URL-safe tokens, so unicode shouldn't appear
        token = csrf.generate_token()

        # Should be ASCII only
        assert token.isascii()

    def test_very_long_token_comparison(self, csrf):
        """Test comparison of very long tokens."""
        long_token = "a" * 10000

        # Should handle long tokens without issues
        assert csrf.validate_token(long_token, long_token) is True
        assert csrf.validate_token(long_token, long_token + "b") is False

    def test_special_characters_in_validation(self, csrf):
        """Test validation with special characters."""
        # Even though our tokens are URL-safe, validation should handle any input
        special_token = "!@#$%^&*()"

        assert csrf.validate_token(special_token, special_token) is True
        assert csrf.validate_token(special_token, "different") is False
