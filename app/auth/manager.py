# app/auth/manager.py
"""
Harbor Authentication Manager

Central authentication management for users and API keys.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api_keys import APIKeyManager, get_api_key_manager
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
        self.is_success = success  # Renamed from 'success' to avoid conflict
        self.user = user
        self.session = session
        self.api_key = api_key
        self.error_message = error_message
        self.requires_mfa = requires_mfa
        self.account_locked = account_locked

    @property
    def success(self) -> bool:
        """Backward compatibility property for success attribute."""
        return self.is_success

    @classmethod
    def create_success(  # Renamed from 'success' to avoid conflict
        cls,
        user: User,
        session: SessionData | None = None,
        api_key: APIKey | None = None,
    ) -> "AuthenticationResult":
        """Create a successful authentication result."""
        return cls(success=True, user=user, session=session, api_key=api_key)

    @classmethod
    def failed(cls, error_message: str) -> "AuthenticationResult":
        """Create a failed authentication result."""
        return cls(success=False, error_message=error_message)


class AuthenticationManager:
    """
    Manages authentication for Harbor.

    Handles both session-based (web UI) and API key authentication.
    """

    def __init__(self) -> None:
        """Initialize authentication manager."""
        self.settings = get_settings()
        self.session_manager = get_session_manager()
        self.api_key_manager = APIKeyManager()  # Create directly
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
        session: AsyncSession,
        api_key: str,
        ip_address: str | None = None,
    ) -> AuthenticationResult:
        """
        Authenticate with API key.

        Args:
            session: Database session
            api_key: API key to authenticate
            ip_address: Client IP address

        Returns:
            Authentication result
        """
        try:
            # Validate API key format
            if not self.api_key_manager.validate_api_key_format(api_key):
                logger.warning(f"Invalid API key format from {ip_address}")
                return AuthenticationResult.failed("Invalid API key")

            # Extract hash for lookup
            key_hash = self.api_key_manager.extract_key_hash(api_key)
            if not key_hash:
                logger.warning(f"Failed to extract key hash from {ip_address}")
                return AuthenticationResult.failed("Invalid API key")

            # Look up API key in database (including inactive/expired)
            from app.db.repositories.api_key import APIKeyRepository

            api_key_repo = APIKeyRepository(session)
            api_key_record = await api_key_repo.get_by_key_hash(key_hash)

            if not api_key_record:
                logger.warning(f"API key not found from {ip_address}")
                return AuthenticationResult.failed("Invalid API key")

            # Check if revoked
            if not api_key_record.is_active:
                logger.warning(f"Revoked API key used from {ip_address}")
                return AuthenticationResult.failed("Invalid API key")

            # Check expiration
            if api_key_record.is_expired():
                logger.warning(f"Expired API key used from {ip_address}")
                return AuthenticationResult.failed("API key has expired")

            # Verify the actual key matches (additional security check)
            if not self.api_key_manager.verify_api_key(
                api_key, api_key_record.key_hash
            ):
                logger.warning(f"API key verification failed from {ip_address}")
                return AuthenticationResult.failed("Invalid API key")

            # Get associated user
            from app.db.repositories.user import UserRepository

            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(
                api_key_record.created_by_user_id
            )  # FIXED: Changed from get to get_by_id

            if not user:
                logger.error(f"User not found for API key {api_key_record.id}")
                return AuthenticationResult.failed("Invalid API key")

            if not user.is_active:
                logger.warning(f"Inactive user attempted API key auth: {user.username}")
                return AuthenticationResult.failed("Account is inactive")

            # Track usage
            await api_key_repo.track_usage(
                api_key_id=api_key_record.id, ip_address=ip_address
            )

            logger.info(
                f"API key authentication successful for user {user.username} from {ip_address}"
            )

            return AuthenticationResult.create_success(
                user=user, api_key=api_key_record
            )

        except Exception as e:
            logger.error(f"API key authentication error: {e}")
            return AuthenticationResult.failed("Authentication failed")

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
