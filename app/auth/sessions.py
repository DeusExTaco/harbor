"""
Harbor Session Management

Secure session handling with HTTP-only cookies and CSRF protection.
"""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from app.config import get_settings
from app.utils.logging import get_logger


logger = get_logger(__name__)


class SessionData:
    """Container for session data."""

    def __init__(
        self,
        session_id: str,
        user_id: int,
        username: str,
        is_admin: bool = False,
        csrf_token: str | None = None,
        created_at: datetime | None = None,
        expires_at: datetime | None = None,
        last_activity: datetime | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ):
        """Initialize session data."""
        self.session_id = session_id
        self.user_id = user_id
        self.username = username
        self.is_admin = is_admin
        self.csrf_token = csrf_token or self._generate_csrf_token()
        self.created_at = created_at or datetime.now(UTC)
        self.expires_at = expires_at
        self.last_activity = last_activity or datetime.now(UTC)
        self.ip_address = ip_address
        self.user_agent = user_agent

    @staticmethod
    def _generate_csrf_token() -> str:
        """Generate a secure CSRF token."""
        return secrets.token_urlsafe(32)

    def is_expired(self) -> bool:
        """Check if session has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(UTC) > self.expires_at

    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "username": self.username,
            "is_admin": self.is_admin,
            "csrf_token": self.csrf_token,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_activity": self.last_activity.isoformat()
            if self.last_activity
            else None,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionData":
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            username=data["username"],
            is_admin=data.get("is_admin", False),
            csrf_token=data.get("csrf_token"),
            created_at=datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else None,
            expires_at=datetime.fromisoformat(data["expires_at"])
            if data.get("expires_at")
            else None,
            last_activity=datetime.fromisoformat(data["last_activity"])
            if data.get("last_activity")
            else None,
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
        )


class SessionManager:
    """
    Manages user sessions with in-memory storage.

    Note: For production, this should use Redis or database storage.
    Current implementation is suitable for single-instance home lab deployment.
    """

    def __init__(self) -> None:
        """Initialize session manager."""
        self.settings = get_settings()
        self._sessions: dict[str, SessionData] = {}
        self._user_sessions: dict[int, set[str]] = {}  # Track sessions per user

    def create_session(
        self,
        user_id: int,
        username: str,
        is_admin: bool = False,
        ip_address: str | None = None,
        user_agent: str | None = None,
        remember_me: bool = False,
    ) -> SessionData:
        """
        Create a new session for a user.

        Args:
            user_id: ID of the user
            username: Username for the session
            is_admin: Whether user is an admin
            ip_address: Client IP address
            user_agent: Client user agent
            remember_me: Whether to extend session timeout

        Returns:
            Created session data
        """
        # Generate secure session ID
        session_id = secrets.token_urlsafe(32)

        # Calculate expiration
        timeout_hours = self.settings.security.session_timeout_hours
        if remember_me:
            # Extend timeout for remember me (30 days max)
            timeout_hours = min(timeout_hours * 4, 720)

        expires_at = datetime.now(UTC) + timedelta(hours=timeout_hours)

        # Create session
        session = SessionData(
            session_id=session_id,
            user_id=user_id,
            username=username,
            is_admin=is_admin,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Store session
        self._sessions[session_id] = session

        # Track user's sessions
        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = set()
        self._user_sessions[user_id].add(session_id)

        # Clean up old sessions for this user (max 5 concurrent sessions)
        self._cleanup_user_sessions(user_id, max_sessions=5)

        logger.info(f"Session created for user {username} (ID: {user_id})")
        return session

    def get_session(self, session_id: str) -> SessionData | None:
        """
        Get session by ID.

        Args:
            session_id: Session ID to retrieve

        Returns:
            Session data if found and valid, None otherwise
        """
        session = self._sessions.get(session_id)

        if session is None:
            return None

        # Check expiration
        if session.is_expired():
            self.invalidate_session(session_id)
            return None

        # Update activity
        session.update_activity()

        return session

    def invalidate_session(self, session_id: str) -> bool:
        """
        Invalidate a session.

        Args:
            session_id: Session ID to invalidate

        Returns:
            True if session was invalidated
        """
        session = self._sessions.get(session_id)

        if session:
            # Remove from session store
            del self._sessions[session_id]

            # Remove from user's sessions
            if session.user_id in self._user_sessions:
                self._user_sessions[session.user_id].discard(session_id)
                if not self._user_sessions[session.user_id]:
                    del self._user_sessions[session.user_id]

            logger.info(f"Session invalidated for user {session.username}")
            return True

        return False

    def invalidate_user_sessions(self, user_id: int) -> int:
        """
        Invalidate all sessions for a user.

        Args:
            user_id: User ID whose sessions to invalidate

        Returns:
            Number of sessions invalidated
        """
        if user_id not in self._user_sessions:
            return 0

        session_ids = list(self._user_sessions[user_id])
        count = 0

        for session_id in session_ids:
            if self.invalidate_session(session_id):
                count += 1

        return count

    def validate_csrf_token(self, session_id: str, csrf_token: str) -> bool:
        """
        Validate CSRF token for a session.

        Args:
            session_id: Session ID
            csrf_token: CSRF token to validate

        Returns:
            True if token is valid
        """
        session = self.get_session(session_id)

        if session is None:
            return False

        return secrets.compare_digest(session.csrf_token, csrf_token)

    def refresh_session(self, session_id: str) -> SessionData | None:
        """
        Refresh a session's expiration time.

        Args:
            session_id: Session ID to refresh

        Returns:
            Updated session data if found
        """
        session = self.get_session(session_id)

        if session:
            timeout_hours = self.settings.security.session_timeout_hours
            session.expires_at = datetime.now(UTC) + timedelta(hours=timeout_hours)
            session.update_activity()
            logger.debug(f"Session refreshed for user {session.username}")
            return session

        return None

    def _cleanup_user_sessions(self, user_id: int, max_sessions: int = 5) -> None:
        """
        Clean up old sessions for a user, keeping only the most recent.

        Args:
            user_id: User ID to clean up sessions for
            max_sessions: Maximum concurrent sessions allowed
        """
        if user_id not in self._user_sessions:
            return

        user_session_ids = self._user_sessions[user_id]

        if len(user_session_ids) <= max_sessions:
            return

        # Get all user's sessions with timestamps
        sessions_with_time: list[tuple[str, datetime]] = []
        for sid in user_session_ids:
            if sid in self._sessions:
                session = self._sessions[sid]
                sessions_with_time.append((sid, session.created_at))

        # Sort by creation time (oldest first)
        sessions_with_time.sort(key=lambda x: x[1])

        # Remove oldest sessions
        sessions_to_remove = len(sessions_with_time) - max_sessions
        for sid, _ in sessions_with_time[:sessions_to_remove]:
            self.invalidate_session(sid)

        logger.info(f"Cleaned up {sessions_to_remove} old sessions for user {user_id}")

    def cleanup_expired_sessions(self) -> int:
        """
        Clean up all expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        expired_sessions = []

        for session_id, session in self._sessions.items():
            if session.is_expired():
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            self.invalidate_session(session_id)

        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

        return len(expired_sessions)

    def get_session_count(self) -> int:
        """Get total number of active sessions."""
        return len(self._sessions)

    def get_user_session_count(self, user_id: int) -> int:
        """Get number of active sessions for a user."""
        return len(self._user_sessions.get(user_id, set()))

    async def initialize(self) -> None:
        """
        Initialize the session manager.

        This is called during application startup to ensure the session
        manager is ready for use.
        """
        # Clean up any expired sessions on startup
        expired_count = self.cleanup_expired_sessions()
        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired sessions on startup")

        logger.debug("Session manager initialized")

    async def close(self) -> None:
        """
        Clean up session manager resources.

        This is called during application shutdown.
        """
        # Clear all sessions on shutdown
        session_count = len(self._sessions)
        self._sessions.clear()
        self._user_sessions.clear()

        if session_count > 0:
            logger.info(f"Cleared {session_count} sessions on shutdown")

        logger.debug("Session manager closed")


# Global session manager instance
_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """Get the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
