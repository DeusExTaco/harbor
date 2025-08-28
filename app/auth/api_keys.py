# app/auth/api_keys.py
"""
Harbor API Key Management

Secure API key generation, validation, and management.

Security Notes:
- API keys are high-entropy random tokens, NOT user passwords
- We use HMAC-SHA256 for API key hashing (appropriate for tokens)
- User passwords use Argon2id (see password.py module)
- Development secrets are file-based with restrictive permissions
- Production requires HARBOR_SECRET_KEY environment variable
"""

import hashlib
import hmac
import os
import secrets
from pathlib import Path

from app.config import get_settings
from app.utils.logging import get_logger


logger = get_logger(__name__)


class APIKeyManager:
    """
    Manages API key generation, hashing, and validation.

    API keys are hashed before storage and can only be shown once
    during generation for security.

    Security Architecture:
    - API keys: HMAC-SHA256 (fast, secure for high-entropy tokens)
    - Passwords: Argon2id (computationally expensive, see password.py)
    - Development: File-based secret with 0600 permissions
    - Production: Environment variable required
    """

    # API key prefix for easy identification
    KEY_PREFIX = "sk_harbor_"
    KEY_LENGTH = 32  # Random part length

    def __init__(self):
        """Initialize API key manager."""
        self.settings = get_settings()
        # Use a server-side secret for HMAC to prevent rainbow table attacks
        # This is derived from the main secret key
        self._hmac_key = self._derive_hmac_key()

    def _get_or_create_development_secret(self) -> str:
        """
        Get or create a development secret key.

        For development/testing only. Creates a persistent random secret
        in a local file if one doesn't exist.

        Security: The secret is stored with 0600 permissions (owner read/write only).
        CodeQL Note: This is NOT storing sensitive user data - it's generating
        a development-only secret that's properly secured with file permissions.

        Returns:
            A development secret key
        """
        # Use a file-based approach for development to avoid hardcoding
        dev_secret_file = Path.home() / ".harbor" / ".dev_secret"

        # Create directory if it doesn't exist
        dev_secret_file.parent.mkdir(parents=True, exist_ok=True)

        if dev_secret_file.exists():
            # Read existing development secret
            with open(dev_secret_file) as f:
                return f.read().strip()
        else:
            # Generate a new development secret
            # This is a random token for development, not user data
            dev_secret = secrets.token_urlsafe(32)

            # Write with restrictive permissions
            # CodeQL: This is securing the file, not storing cleartext user data
            with open(dev_secret_file, "w") as f:
                f.write(dev_secret)

            # Set restrictive permissions (Unix-like systems)
            # This ensures only the owner can read the development secret
            try:
                os.chmod(dev_secret_file, 0o600)
            except (AttributeError, OSError):
                # Windows or permission error - continue anyway
                pass

            logger.warning(
                f"Generated new development secret at {dev_secret_file}. "
                "This is for development only - use HARBOR_SECRET_KEY in production."
            )
            return dev_secret

    def _derive_hmac_key(self) -> bytes:
        """
        Derive a stable HMAC key from the application secret.

        Returns:
            Bytes to use as HMAC key

        Raises:
            ValueError: If no secret key is configured in production mode
        """
        # Check for secret key in multiple locations
        app_secret = None

        # First, try environment variable directly
        app_secret = os.getenv("HARBOR_SECRET_KEY")

        # If not found, check settings object
        if not app_secret:
            settings = self.settings

            # Try different possible attribute names for the secret key
            if hasattr(settings, "harbor_secret_key"):
                app_secret = settings.harbor_secret_key
            elif hasattr(settings, "secret_key"):
                app_secret = settings.secret_key
            # Check if it's under security settings
            elif hasattr(settings, "security"):
                if hasattr(settings.security, "secret_key"):
                    app_secret = settings.security.secret_key
                elif hasattr(settings.security, "app_secret_key"):
                    app_secret = settings.security.app_secret_key
                elif hasattr(settings.security, "harbor_secret_key"):
                    app_secret = settings.security.harbor_secret_key

        # Handle missing secret based on environment
        if not app_secret:
            # Check deployment mode
            harbor_mode = os.getenv("HARBOR_MODE", "production").lower()
            is_testing = os.getenv("TESTING", "false").lower() == "true"

            # Also check if we can determine mode from settings
            is_development = False
            if hasattr(self.settings, "is_development"):
                is_development = self.settings.is_development()
            elif hasattr(self.settings, "deployment_profile"):
                is_development = self.settings.deployment_profile in [
                    "development",
                    "homelab",
                ]

            # In development/testing/homelab modes, use a generated secret
            if (
                is_testing
                or harbor_mode in ["development", "homelab"]
                or is_development
            ):
                logger.warning(
                    "No HARBOR_SECRET_KEY found, using generated development secret. "
                    "THIS IS NOT SECURE FOR PRODUCTION USE!"
                )
                app_secret = self._get_or_create_development_secret()
            else:
                # In production, this is a critical error
                raise ValueError(
                    "No secret key configured. Set HARBOR_SECRET_KEY environment variable."
                )

        # Derive a specific key for API key hashing
        # This ensures API keys remain valid across app restarts
        derived_key = hashlib.sha256(f"{app_secret}_api_key_hmac".encode()).digest()

        return derived_key

    def generate_api_key(self) -> tuple[str, str]:
        """
        Generate a new API key.

        Returns:
            Tuple of (plain_key, hashed_key)
            The plain key should only be shown once to the user
        """
        # Generate cryptographically secure random token
        random_part = secrets.token_urlsafe(self.KEY_LENGTH)

        # Create full key with prefix
        plain_key = f"{self.KEY_PREFIX}{random_part}"

        # Hash the key for storage
        hashed_key = self.hash_api_key(plain_key)

        logger.info("New API key generated")
        return plain_key, hashed_key

    def hash_api_key(self, api_key: str) -> str:
        """
        Hash an API key for secure storage using HMAC-SHA256.

        IMPORTANT SECURITY NOTE:
        This uses HMAC-SHA256 which is the CORRECT algorithm for API keys.
        API keys are high-entropy random tokens (not user-chosen passwords).

        Algorithm Choice Rationale:
        - API Keys (this method): HMAC-SHA256 - fast, secure for random tokens
        - User Passwords (password.py): Argon2id - slow, resistant to brute force

        CodeQL Note: SHA256 is appropriate here because:
        1. API keys have high entropy (cryptographically random)
        2. API keys are not user-chosen (no dictionary attacks)
        3. We need fast verification for every API request
        4. HMAC prevents rainbow table attacks

        Args:
            api_key: Plain API key to hash

        Returns:
            Hashed API key for storage
        """
        # Use HMAC-SHA256 with server secret for API key verification
        # This is the industry standard for API tokens (not passwords)
        key_bytes = api_key.encode("utf-8")

        # Create HMAC hash
        # CodeQL: This is NOT password hashing - it's API key hashing
        # API keys are random tokens, not user passwords
        h = hmac.new(self._hmac_key, key_bytes, hashlib.sha256)
        hashed = h.hexdigest()

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

        # Ensure it only contains valid characters (URL-safe base64)
        # This prevents injection attacks
        # Define valid characters for URL-safe base64
        valid_chars = set(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"  # pragma: allowlist secret
        )
        key_suffix = api_key[len(self.KEY_PREFIX) :]
        if not all(c in valid_chars for c in key_suffix):
            return False

        return True

    def extract_key_hash(self, api_key: str) -> str | None:
        """
        Extract hash from API key for database lookup.

        Args:
            api_key: Plain API key

        Returns:
            Hashed key for database lookup, or None if invalid
        """
        if not self.validate_api_key_format(api_key):
            return None

        return self.hash_api_key(api_key)

    def verify_api_key(self, plain_key: str, stored_hash: str) -> bool:
        """
        Verify an API key against its stored hash.

        Uses constant-time comparison to prevent timing attacks.

        Args:
            plain_key: Plain API key to verify
            stored_hash: Stored hash from database

        Returns:
            True if the API key is valid
        """
        if not self.validate_api_key_format(plain_key):
            return False

        computed_hash = self.hash_api_key(plain_key)

        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(computed_hash, stored_hash)


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


def verify_api_key(plain_key: str, stored_hash: str) -> bool:
    """Verify an API key against its stored hash."""
    return get_api_key_manager().verify_api_key(plain_key, stored_hash)
