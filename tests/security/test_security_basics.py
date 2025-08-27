"""
Security test basics
Verify basic security configurations and practices
"""

import pytest


@pytest.mark.security
def test_no_hardcoded_secrets():
    """Verify no obvious secrets in test files"""
    # Secret scanning is handled by bandit in pre-commit hooks
    pytest.skip("Secret scanning is handled by bandit in pre-commit hooks")


@pytest.mark.security
def test_secure_defaults():
    """Test that secure defaults are used"""
    from app.config import get_settings

    settings = get_settings()

    # Test security defaults based on deployment profile
    if settings.deployment_profile.value == "production":
        # Production should have strict requirements
        assert settings.security.require_https is True
        assert settings.security.session_timeout_hours <= 24
        assert settings.security.password_min_length >= 8
    elif settings.deployment_profile.value == "development":
        # Development has relaxed requirements for easier testing
        assert settings.security.password_min_length >= 6  # Development allows 6
        assert settings.security.session_timeout_hours > 0
    else:  # homelab
        # Homelab has moderate requirements
        assert settings.security.password_min_length >= 6
        assert settings.security.session_timeout_hours > 0

    # Common requirements for all profiles
    assert settings.security.api_rate_limit_per_hour > 0
