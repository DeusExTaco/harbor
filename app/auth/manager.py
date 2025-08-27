# app/auth/manager.py
"""
Harbor Authentication Manager

Central authentication management for users and API keys.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api_keys import get_api_key_manager
from app.auth.csrf import get_csrf_protection
from app.auth.password import verify_password
from app.auth.sessions import SessionData, get_session_manager
from app.config import get_settings
from app.db.models.api_key import APIKey
from app.db.models.user import User
from app.utils.logging import get_logger


logger = get_logger(__name__)


def sanitize_for_logging(value: str) -> str:
    """
    Sanitize user input for safe logging.

    Removes newlines and carriage returns to prevent log injection attacks.
    Limits length to prevent excessive log entries.

    Args:
        value: The string to sanitize

    Returns:
        Sanitized string safe for logging
    """
    if not value:
        return ""

    # Remove newlines, carriage returns, and other control characters
    sanitized = value.replace("\r", "").replace("\n", "").replace("\t", " ")

    # Remove any other control characters
    sanitized = "".join(char if ord(char) >= 32 else "" for char in sanitized)

    # Limit length to prevent log flooding
    max_length = 100
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."

    return sanitized


class AuthenticationResult:
    """Container for authentication result."""

    def __init__(
        self,
        success: bool,
        user: User | None = None,
        session: SessionData | None = None,
        api_key: APIKey | None = None,
        error_message: str | None = None,
        requires_mfa: bool = False,
        account_locked: bool = False,
    ):
        """Initialize authentication result."""
        self.success = success
        self.user = user
        self.session = session
        self.api_key = api_key
        self.error_message = error_message
        self.requires_mfa = requires_mfa
        self.account_locked = account_locked


class AuthenticationManager:
    """
    Manages authentication for Harbor.

    Handles both session-based (web UI) and API key authentication.
    """

    def __init__(self):
        """Initialize authentication manager."""
        self.settings = get_settings()
        self.session_manager = get_session_manager()
        self.api_key_manager = get_api_key_manager()
        self.csrf_protection = get_csrf_protection()

        # Account lockout configuration
        self.max_login_attempts = 5
        self.lockout_duration_minutes = 30

        # Track failed login attempts (in-memory for now)
        self._failed_attempts: dict[str, list[datetime]] = {}

    async def authenticate_user(
        self,
        db: AsyncSession,
        username: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        remember_me: bool = False,
    ) -> AuthenticationResult:
        """
        Authenticate a user with username and password.

        Args:
            db: Database session
            username: Username to authenticate
            password: Password to verify
            ip_address: Client IP address
            user_agent: Client user agent
            remember_me: Whether to extend session timeout

        Returns:
            Authentication result
        """
        # Check account lockout
        if self._is_account_locked(username):
            safe_username = sanitize_for_logging(username)
            logger.warning(f"Login attempt for locked account: {safe_username}")
            return AuthenticationResult(
                success=False,
                error_message="Account temporarily locked due to too many failed attempts",
                account_locked=True,
            )

        # Find user
        stmt = select(User).where(User.username == username)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            self._record_failed_attempt(username)
            safe_username = sanitize_for_logging(username)
            logger.warning(f"Login attempt for non-existent user: {safe_username}")
            return AuthenticationResult(
                success=False,
                error_message="Invalid username or password",
            )

        # Check if user is active
        if not user.is_active:
            safe_username = sanitize_for_logging(username)
            logger.warning(f"Login attempt for inactive user: {safe_username}")
            return AuthenticationResult(
                success=False,
                error_message="Account is disabled",
            )

        # Verify password
        if not verify_password(password, user.password_hash):
            self._record_failed_attempt(username)
            safe_username = sanitize_for_logging(username)
            logger.warning(f"Failed login attempt for user: {safe_username}")

            # Update failed login count in database
            user.failed_login_count = (user.failed_login_count or 0) + 1
            user.last_failed_login_at = datetime.now(UTC)
            await db.commit()

            return AuthenticationResult(
                success=False,
                error_message="Invalid username or password",
            )

        # Clear failed attempts on successful login
        self._clear_failed_attempts(username)

        # Check if MFA is enabled (future feature)
        if user.mfa_enabled:
            safe_username = sanitize_for_logging(username)
            logger.info(f"MFA required for user: {safe_username}")
            # TODO: Implement MFA in M7+
            # For now, MFA is behind a feature flag and not implemented

        # Create session
        session = self.session_manager.create_session(
            user_id=user.id,
            username=user.username,
            is_admin=user.is_admin,
            ip_address=ip_address,
            user_agent=user_agent,
            remember_me=remember_me,
        )

        # Update user login info
        user.last_login_at = datetime.now(UTC)
        user.last_login_ip = ip_address
        user.login_count = (user.login_count or 0) + 1
        user.failed_login_count = 0  # Reset failed count
        await db.commit()

        safe_username = sanitize_for_logging(username)
        logger.info(f"User {safe_username} logged in successfully")

        return AuthenticationResult(
            success=True,
            user=user,
            session=session,
        )

    async def authenticate_api_key(
        self,
        db: AsyncSession,
        api_key: str,
        ip_address: str | None = None,
    ) -> AuthenticationResult:
        """
        Authenticate with API key.

        Args:
            db: Database session
            api_key: API key to authenticate
            ip_address: Client IP address

        Returns:
            Authentication result
        """
        # Validate API key format
        if not self.api_key_manager.validate_api_key_format(api_key):
            logger.warning("Invalid API key format")
            return AuthenticationResult(
                success=False,
                error_message="Invalid API key",
            )

        # Hash the API key for lookup
        key_hash = self.api_key_manager.hash_api_key(api_key)

        # Find API key in database
        stmt = select(APIKey).where(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True,
        )
        result = await db.execute(stmt)
        api_key_record = result.scalar_one_or_none()

        if not api_key_record:
            logger.warning(f"API key authentication failed from {ip_address}")
            return AuthenticationResult(
                success=False,
                error_message="Invalid API key",
            )

        # Check expiration
        if api_key_record.expires_at and datetime.now(UTC) > api_key_record.expires_at:
            safe_key_name = sanitize_for_logging(api_key_record.name)
            logger.warning(f"Expired API key used: {safe_key_name}")
            return AuthenticationResult(
                success=False,
                error_message="API key has expired",
            )

        # Get associated user
        user_stmt = select(User).where(User.id == api_key_record.created_by_user_id)
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        if not user or not user.is_active:
            safe_key_name = sanitize_for_logging(api_key_record.name)
            logger.warning(f"API key associated with invalid user: {safe_key_name}")
            return AuthenticationResult(
                success=False,
                error_message="API key is invalid",
            )

        # Update API key usage
        api_key_record.last_used_at = datetime.now(UTC)
        api_key_record.last_used_ip = ip_address
        api_key_record.usage_count = (api_key_record.usage_count or 0) + 1
        await db.commit()

        safe_key_name = sanitize_for_logging(api_key_record.name)
        logger.info(f"API key {safe_key_name} authenticated successfully")

        return AuthenticationResult(
            success=True,
            user=user,
            api_key=api_key_record,
        )

    def validate_session(self, session_id: str) -> SessionData | None:
        """
        Validate a session ID.

        Args:
            session_id: Session ID to validate

        Returns:
            Session data if valid, None otherwise
        """
        return self.session_manager.get_session(session_id)

    def logout(self, session_id: str) -> bool:
        """
        Log out a user by invalidating their session.

        Args:
            session_id: Session ID to invalidate

        Returns:
            True if logout successful
        """
        return self.session_manager.invalidate_session(session_id)

    def logout_user(self, user_id: int) -> int:
        """
        Log out all sessions for a user.

        Args:
            user_id: User ID to log out

        Returns:
            Number of sessions invalidated
        """
        return self.session_manager.invalidate_user_sessions(user_id)

    def validate_csrf_token(self, session_id: str, csrf_token: str) -> bool:
        """
        Validate CSRF token for a session.

        Args:
            session_id: Session ID
            csrf_token: CSRF token to validate

        Returns:
            True if valid
        """
        return self.session_manager.validate_csrf_token(session_id, csrf_token)

    def _is_account_locked(self, username: str) -> bool:
        """Check if account is locked due to failed attempts."""
        if username not in self._failed_attempts:
            return False

        # Remove old attempts
        cutoff_time = datetime.now(UTC) - timedelta(
            minutes=self.lockout_duration_minutes
        )
        self._failed_attempts[username] = [
            attempt
            for attempt in self._failed_attempts[username]
            if attempt > cutoff_time
        ]

        # Check if still locked
        return len(self._failed_attempts[username]) >= self.max_login_attempts

    def _record_failed_attempt(self, username: str) -> None:
        """Record a failed login attempt."""
        if username not in self._failed_attempts:
            self._failed_attempts[username] = []

        self._failed_attempts[username].append(datetime.now(UTC))

        # Keep only recent attempts
        cutoff_time = datetime.now(UTC) - timedelta(
            minutes=self.lockout_duration_minutes
        )
        self._failed_attempts[username] = [
            attempt
            for attempt in self._failed_attempts[username]
            if attempt > cutoff_time
        ]

    def _clear_failed_attempts(self, username: str) -> None:
        """Clear failed login attempts for a user."""
        if username in self._failed_attempts:
            del self._failed_attempts[username]


# Global authentication manager instance
_auth_manager: AuthenticationManager | None = None


def get_auth_manager() -> AuthenticationManager:
    """Get the global authentication manager instance."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthenticationManager()
    return _auth_manager
