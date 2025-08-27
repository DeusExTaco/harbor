# app/auth/api_keys.py
"""
Harbor API Key Management

Secure API key generation, validation, and management.
"""

import hashlib
import secrets

from app.config import get_settings
from app.utils.logging import get_logger


logger = get_logger(__name__)


class APIKeyManager:
    """
    Manages API key generation, hashing, and validation.

    API keys are hashed before storage and can only be shown once
    during generation for security.
    """

    # API key prefix for easy identification
    KEY_PREFIX = "sk_harbor_"
    KEY_LENGTH = 32  # Random part length

    def __init__(self):
        """Initialize API key manager."""
        self.settings = get_settings()

    def generate_api_key(self) -> tuple[str, str]:
        """
        Generate a new API key.

        Returns:
            Tuple of (plain_key, hashed_key)
            The plain key should only be shown once to the user
        """
        # Generate random key
        random_part = secrets.token_urlsafe(self.KEY_LENGTH)

        # Create full key with prefix
        plain_key = f"{self.KEY_PREFIX}{random_part}"

        # Hash the key for storage
        hashed_key = self.hash_api_key(plain_key)

        logger.info("New API key generated")
        return plain_key, hashed_key

    def hash_api_key(self, api_key: str) -> str:
        """
        Hash an API key for secure storage.

        Args:
            api_key: Plain API key to hash

        Returns:
            Hashed API key
        """
        # Use SHA-256 for API key hashing (faster than argon2 for this use case)
        # API keys are already high-entropy random strings
        key_bytes = api_key.encode("utf-8")
        hashed = hashlib.sha256(key_bytes).hexdigest()
        return hashed

    def validate_api_key_format(self, api_key: str) -> bool:
        """
        Validate API key format.

        Args:
            api_key: API key to validate

        Returns:
            True if format is valid
        """
        if not api_key:
            return False

        # Check prefix
        if not api_key.startswith(self.KEY_PREFIX):
            return False

        # Check minimum length
        if len(api_key) < len(self.KEY_PREFIX) + 20:
            return False

        return True

    def extract_key_hash(self, api_key: str) -> str | None:
        """
        Extract hash from API key for database lookup.

        Args:
            api_key: Plain API key

        Returns:
            Hashed key for database lookup
        """
        if not self.validate_api_key_format(api_key):
            return None

        return self.hash_api_key(api_key)


# Global API key manager instance
_api_key_manager: APIKeyManager | None = None


def get_api_key_manager() -> APIKeyManager:
    """Get the global API key manager instance."""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    return _api_key_manager


# Convenience functions
def generate_api_key() -> tuple[str, str]:
    """Generate a new API key."""
    return get_api_key_manager().generate_api_key()


def hash_api_key(api_key: str) -> str:
    """Hash an API key."""
    return get_api_key_manager().hash_api_key(api_key)


def validate_api_key(api_key: str) -> bool:
    """Validate API key format."""
    return get_api_key_manager().validate_api_key_format(api_key)
