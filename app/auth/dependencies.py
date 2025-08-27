# app/auth/dependencies.py
"""
Harbor Authentication Dependencies

FastAPI dependency injection for authentication and authorization.
"""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.manager import get_auth_manager
from app.auth.sessions import SessionData
from app.config import get_settings
from app.db.models.user import User
from app.db.session import get_db
from app.utils.logging import get_logger


logger = get_logger(__name__)

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_session(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SessionData | None:
    """
    Get current session from cookie.

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        Session data if valid
    """
    # Get session ID from cookie
    session_id = request.cookies.get("harbor_session")

    if not session_id:
        return None

    # Validate session
    auth_manager = get_auth_manager()
    session = auth_manager.validate_session(session_id)

    return session


async def get_current_user(
    session: SessionData | None = Depends(get_current_session),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current authenticated user.

    Supports both session-based and API key authentication.

    Args:
        session: Session from cookie
        credentials: Bearer token credentials
        x_api_key: API key from header
        db: Database session

    Returns:
        Current user

    Raises:
        HTTPException: If not authenticated
    """
    settings = get_settings()
    auth_manager = get_auth_manager()

    # Check session first (web UI)
    if session:
        # Get user from database
        user = await db.get(User, session.user_id)
        if user and user.is_active:
            return user

    # Check API key authentication
    api_key = None

    # Try X-API-Key header first
    if x_api_key:
        api_key = x_api_key
    # Then try Bearer token
    elif credentials and credentials.scheme == "Bearer":
        api_key = credentials.credentials

    if api_key:
        # Get client IP for logging
        # Note: In production, use proper IP extraction considering proxies
        result = await auth_manager.authenticate_api_key(
            db, api_key, ip_address="unknown"
        )

        if result.success and result.user:
            return result.user

    # If API key is required but not valid, raise error
    if settings.security.api_key_required:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # For development/home lab without required auth
    if not settings.security.api_key_required and settings.deployment_profile.value in [
        "homelab",
        "development",
    ]:
        # Get or create default admin user
        admin_user = await db.get(User, 1)
        if admin_user:
            return admin_user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current active user.

    Args:
        current_user: Current user from auth

    Returns:
        Active user

    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


async def get_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Get current user if admin.

    Args:
        current_user: Current active user

    Returns:
        Admin user

    Raises:
        HTTPException: If user is not admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def validate_csrf_token(
    request: Request,
    session: SessionData | None = Depends(get_current_session),
    x_csrf_token: str | None = Header(None, alias="X-CSRF-Token"),
) -> bool:
    """
    Validate CSRF token for state-changing operations.

    Args:
        request: FastAPI request
        session: Current session
        x_csrf_token: CSRF token from header

    Returns:
        True if valid

    Raises:
        HTTPException: If CSRF validation fails
    """
    # Skip CSRF for GET, HEAD, OPTIONS
    if request.method in ["GET", "HEAD", "OPTIONS"]:
        return True

    # Skip if no session (API key auth)
    if not session:
        return True

    # Require CSRF token for session-based auth
    if not x_csrf_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token required",
        )

    auth_manager = get_auth_manager()
    if not auth_manager.validate_csrf_token(session.session_id, x_csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token",
        )

    return True


# Type aliases for cleaner function signatures
CurrentUser = Annotated[User, Depends(get_current_active_user)]
AdminUser = Annotated[User, Depends(get_admin_user)]
DatabaseSession = Annotated[AsyncSession, Depends(get_db)]
CSRFToken = Annotated[bool, Depends(validate_csrf_token)]
