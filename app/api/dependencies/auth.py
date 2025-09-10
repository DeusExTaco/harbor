# app/api/dependencies/auth.py
"""
Authentication dependencies for FastAPI routes.

Implementation: M0 Milestone - Foundation Phase
Part of: Authentication Foundation (v1: Simple)
"""

from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, HTTPBasic, HTTPBasicCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.db.repositories.user import UserRepository
from app.db.session import get_session
from app.utils.logging import get_logger


logger = get_logger(__name__)

# Security schemes
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
http_basic = HTTPBasic(auto_error=False)


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
    api_key: str | None = Depends(api_key_header),
    credentials: HTTPBasicCredentials | None = Depends(http_basic),
) -> User | None:
    """
    Get current authenticated user from session, API key, or HTTP Basic.

    Args:
        request: FastAPI request object
        session: Database session
        api_key: API key from header
        credentials: HTTP Basic credentials

    Returns:
        User object if authenticated, None otherwise
    """

    # Check if user is already in request state (from session middleware)
    if hasattr(request.state, "user") and request.state.user:
        return request.state.user

    # Check API key authentication
    if api_key:
        # TODO: M0 - Implement API key validation
        # For now, return None (structure in place)
        logger.debug("API key authentication not yet implemented")

    # Check HTTP Basic authentication
    if credentials:
        # TODO: M0 - Implement basic auth validation against database
        # For now, return None (structure in place)
        logger.debug("HTTP Basic authentication not yet implemented")

    return None


async def require_auth(
    user: User | None = Depends(get_current_user),
) -> User:
    """
    Dependency that requires an authenticated user.
    Also checks that the user account is active.

    Args:
        user: User from get_current_user dependency

    Returns:
        User object if authenticated and active

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if authenticated but inactive
    """
    if not user:
        logger.warning("Authentication required but no user found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        logger.warning(f"User {user.username} is not active")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


async def require_admin(
    user: User = Depends(require_auth),
) -> User:
    """
    Dependency that requires an admin user.
    Note: User must already be authenticated and active (via require_auth).

    Args:
        user: User from require_auth dependency

    Returns:
        User object if admin

    Raises:
        HTTPException: 403 if not admin
    """
    if not user.is_admin:
        logger.warning(f"Admin access required but user {user.username} is not admin")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


async def optional_auth(
    user: User | None = Depends(get_current_user),
) -> User | None:
    """
    Optional authentication - doesn't fail if no auth provided.
    Note: This does NOT check if the user is active, since it's optional.

    If you need to check for active users in optional auth scenarios,
    check user.is_active manually after calling this dependency.

    Args:
        user: User from get_current_user dependency

    Returns:
        User object if authenticated, None otherwise
    """
    return user
