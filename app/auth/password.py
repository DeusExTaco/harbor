# app/auth/password.py
"""
Harbor Password Management

Secure password hashing and verification using argon2id.
Implements OWASP best practices for password security.
"""

import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerificationError, VerifyMismatchError

from app.config import get_settings
from app.utils.logging import get_logger


logger = get_logger(__name__)

# Argon2id configuration following OWASP recommendations
# Memory: 64MB, iterations: 3, parallelism: 4
_password_hasher = PasswordHasher(
    memory_cost=65536,  # 64MB
    time_cost=3,  # 3 iterations
    parallelism=4,  # 4 parallel threads
    hash_len=32,  # 32 byte hash
    salt_len=16,  # 16 byte salt
)


class PasswordManager:
    """
    Manages password hashing, verification, and validation.

    Implements secure password handling with configurable strength requirements
    based on deployment profile.
    """

    def __init__(self):
        """Initialize password manager with configuration."""
        self.settings = get_settings()
        self.min_length = self.settings.security.password_min_length
        self.require_special = self.settings.security.password_require_special

    def hash_password(self, password: str) -> str:
        """
        Hash a password using argon2id.

        Args:
            password: Plain text password to hash

        Returns:
            Hashed password string

        Raises:
            ValueError: If password is empty
        """
        if not password:
            raise ValueError("Password cannot be empty")

        try:
            hashed = _password_hasher.hash(password)
            logger.debug("Password hashed successfully")
            return hashed
        except Exception as e:
            logger.error(f"Password hashing failed: {e}")
            raise ValueError("Failed to hash password") from e

    def verify_password(self, password: str, hashed: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            password: Plain text password to verify
            hashed: Hashed password to verify against

        Returns:
            True if password matches, False otherwise
        """
        if not password or not hashed:
            return False

        try:
            _password_hasher.verify(hashed, password)

            # Check if rehashing is needed (argon2 parameters changed)
            if _password_hasher.check_needs_rehash(hashed):
                logger.info("Password hash needs rehashing with updated parameters")
                # Note: Actual rehashing would happen during login

            return True

        except (VerifyMismatchError, VerificationError, InvalidHash):
            return False
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False

    def validate_password_strength(self, password: str) -> tuple[bool, list[str]]:
        """
        Validate password meets strength requirements.

        Args:
            password: Password to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check minimum length
        if len(password) < self.min_length:
            errors.append(
                f"Password must be at least {self.min_length} characters long"
            )

        # Check for special characters if required
        if self.require_special:
            special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
            if not any(char in special_chars for char in password):
                errors.append("Password must contain at least one special character")

        # Additional checks for production environments
        if self.settings.deployment_profile.value == "production":
            # Check for uppercase
            if not any(char.isupper() for char in password):
                errors.append("Password must contain at least one uppercase letter")

            # Check for lowercase
            if not any(char.islower() for char in password):
                errors.append("Password must contain at least one lowercase letter")

            # Check for digits
            if not any(char.isdigit() for char in password):
                errors.append("Password must contain at least one number")

            # Check against common passwords (basic check)
            common_passwords = {"password", "admin", "harbor", "12345678", "qwerty"}
            if password.lower() in common_passwords:
                errors.append("Password is too common")

        return len(errors) == 0, errors

    def generate_secure_password(self, length: int = 16) -> str:
        """
        Generate a cryptographically secure random password.

        Args:
            length: Length of password to generate (default: 16)

        Returns:
            Secure random password
        """
        # Use a character set that avoids ambiguous characters
        charset = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789!@#$%^&*"

        # Ensure minimum length
        length = max(length, self.min_length)

        # Generate password
        password = "".join(secrets.choice(charset) for _ in range(length))

        # Ensure it meets requirements
        valid, _ = self.validate_password_strength(password)
        if not valid:
            # Recursively generate until we get a valid one
            return self.generate_secure_password(length)

        return password

    def needs_rehash(self, hashed: str) -> bool:
        """
        Check if a password hash needs to be rehashed.

        Args:
            hashed: The hashed password to check

        Returns:
            True if rehashing is needed
        """
        try:
            return _password_hasher.check_needs_rehash(hashed)
        except Exception:
            return False


# Global password manager instance
_password_manager: PasswordManager | None = None


def get_password_manager() -> PasswordManager:
    """Get the global password manager instance."""
    global _password_manager
    if _password_manager is None:
        _password_manager = PasswordManager()
    return _password_manager


# Convenience functions
def hash_password(password: str) -> str:
    """Hash a password using the global password manager."""
    return get_password_manager().hash_password(password)


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password using the global password manager."""
    return get_password_manager().verify_password(password, hashed)


def validate_password(password: str) -> tuple[bool, list[str]]:
    """Validate password strength using the global password manager."""
    return get_password_manager().validate_password_strength(password)


def generate_password(length: int = 16) -> str:
    """Generate a secure password using the global password manager."""
    return get_password_manager().generate_secure_password(length)
