# app/auth/csrf.py
"""
Harbor CSRF Protection

Cross-Site Request Forgery protection for web UI.
"""

import secrets

from app.utils.logging import get_logger


logger = get_logger(__name__)


class CSRFProtection:
    """
    CSRF protection using double-submit cookies pattern.
    """

    def __init__(self):
        """Initialize CSRF protection."""
        self.token_length = 32

    def generate_token(self) -> str:
        """
        Generate a new CSRF token.

        Returns:
            Secure random CSRF token
        """
        token = secrets.token_urlsafe(self.token_length)
        logger.debug("CSRF token generated")
        return token

    def validate_token(self, token: str, expected: str) -> bool:
        """
        Validate CSRF token using constant-time comparison.

        Args:
            token: Submitted token
            expected: Expected token

        Returns:
            True if tokens match
        """
        if not token or not expected:
            return False

        # Use constant-time comparison to prevent timing attacks
        return secrets.compare_digest(token, expected)

    def generate_form_token(self, session_token: str) -> str:
        """
        Generate a form-specific CSRF token.

        Args:
            session_token: Session CSRF token

        Returns:
            Form-specific token
        """
        # For now, just return the session token
        # In future, could add form-specific salting
        return session_token


# Global CSRF protection instance
_csrf_protection: CSRFProtection | None = None


def get_csrf_protection() -> CSRFProtection:
    """Get the global CSRF protection instance."""
    global _csrf_protection
    if _csrf_protection is None:
        _csrf_protection = CSRFProtection()
    return _csrf_protection
