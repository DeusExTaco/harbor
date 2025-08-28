# app/api/auth.py
"""
Harbor Authentication API Endpoints

Handles login, logout, session management, and user operations.
"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select

from app.auth.api_keys import generate_api_key
from app.auth.dependencies import (
    AdminUser,
    CSRFToken,
    CurrentUser,
    DatabaseSession,
    get_current_session,
)
from app.auth.manager import get_auth_manager
from app.auth.models import (
    APIKeyRequest,
    APIKeyResponse,
    ChangePasswordRequest,
    CreateUserRequest,
    LoginRequest,
    LoginResponse,
    UserInfo,
)
from app.auth.password import hash_password, validate_password, verify_password
from app.auth.sessions import SessionData
from app.config import get_settings
from app.db.models.api_key import APIKey
from app.db.models.user import User
from app.utils.logging import get_logger


logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


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


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    response: Response,
    login_data: LoginRequest,
    db: DatabaseSession,
) -> LoginResponse:
    """
    Authenticate user and create session.

    Creates a session-based authentication for web UI access.
    Sets an HTTP-only cookie with the session ID.
    """
    # Find user
    stmt = select(User).where(User.username == login_data.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        # Sanitize username before logging to prevent log injection
        safe_username = sanitize_for_logging(login_data.username)
        logger.warning(f"Login attempt for non-existent user: {safe_username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Check if user is active
    if not user.is_active:
        # Use the stored username from database (already validated)
        safe_username = sanitize_for_logging(user.username)
        logger.warning(f"Login attempt for inactive user: {safe_username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Account is disabled"
        )

    # Verify password
    if not verify_password(login_data.password, user.password_hash):
        # Use the stored username from database (already validated)
        safe_username = sanitize_for_logging(user.username)
        logger.warning(f"Failed password for user: {safe_username}")
        # Update failed login count
        user.failed_login_count = (user.failed_login_count or 0) + 1
        user.last_failed_login_at = datetime.now(UTC)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Create session
    auth_manager = get_auth_manager()
    session = auth_manager.session_manager.create_session(
        user_id=user.id,
        username=user.username,
        is_admin=user.is_admin,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        remember_me=login_data.remember_me,
    )

    # Update user login info
    user.last_login_at = datetime.now(UTC)
    user.last_login_ip = request.client.host if request.client else None
    user.login_count = (user.login_count or 0) + 1
    user.failed_login_count = 0
    await db.commit()

    # Set session cookie
    settings = get_settings()
    max_age = settings.security.session_timeout_hours * 3600
    if login_data.remember_me:
        max_age = max_age * 4  # Extend for remember me

    response.set_cookie(
        key="harbor_session",  # pragma: allowlist secret
        value=session.session_id,
        max_age=max_age,
        httponly=True,
        secure=settings.security.require_https,
        samesite="lax",
    )

    # Safe logging of successful login
    safe_username = sanitize_for_logging(user.username)
    logger.info(f"User {safe_username} logged in successfully")

    return LoginResponse(
        success=True,
        message="Login successful",
        user={
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "is_admin": user.is_admin,
        },
        session_id=session.session_id,
        csrf_token=session.csrf_token,
        expires_at=session.expires_at,
    )


@router.post("/logout")
async def logout(
    response: Response,
    session: SessionData | None = Depends(get_current_session),
) -> dict:
    """
    Log out current user and invalidate session.
    """
    if session:
        auth_manager = get_auth_manager()
        auth_manager.logout(session.session_id)
        logger.info(f"User logged out (session: {session.session_id[:8]}...)")

    # Clear session cookie
    response.delete_cookie("harbor_session")

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    current_user: CurrentUser,
) -> UserInfo:
    """
    Get current user information.
    """
    return UserInfo(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        display_name=current_user.display_name,
        is_admin=current_user.is_admin,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login_at=current_user.last_login_at,
        login_count=current_user.login_count or 0,
        failed_login_count=current_user.failed_login_count or 0,
    )


@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: CurrentUser,
    db: DatabaseSession,
    _csrf: CSRFToken,
) -> dict:
    """
    Change current user's password.
    """
    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    # Validate new password strength
    valid, errors = validate_password(password_data.new_password)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Password does not meet requirements", "errors": errors},
        )

    # Update password
    current_user.password_hash = hash_password(password_data.new_password)
    current_user.password_changed_at = datetime.now(UTC)

    # Invalidate all sessions for security
    auth_manager = get_auth_manager()
    auth_manager.logout_user(current_user.id)

    await db.commit()

    # Safe logging
    safe_username = sanitize_for_logging(current_user.username)
    logger.info(f"Password changed for user {safe_username}")

    return {"message": "Password changed successfully. Please log in again."}


@router.post("/users", response_model=UserInfo)
async def create_user(
    user_data: CreateUserRequest,
    admin_user: AdminUser,
    db: DatabaseSession,
    _csrf: CSRFToken,
) -> UserInfo:
    """
    Create a new user (admin only).

    Note: In v1.0, Harbor is single-user. This endpoint is prepared
    for future multi-user support (M8+).
    """
    # Check if user exists
    stmt = select(User).where(User.username == user_data.username)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )

    # Validate password
    valid, errors = validate_password(user_data.password)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Password does not meet requirements", "errors": errors},
        )

    # Create user
    new_user = User(
        username=user_data.username,
        password_hash=hash_password(user_data.password),
        email=user_data.email,
        display_name=user_data.display_name,
        is_admin=user_data.is_admin,
        created_at=datetime.now(UTC),
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Safe logging
    safe_new_username = sanitize_for_logging(new_user.username)
    safe_admin_username = sanitize_for_logging(admin_user.username)
    logger.info(f"User {safe_new_username} created by {safe_admin_username}")

    return UserInfo(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        display_name=new_user.display_name,
        is_admin=new_user.is_admin,
        is_active=new_user.is_active,
        created_at=new_user.created_at,
        last_login_at=new_user.last_login_at,
        login_count=0,
        failed_login_count=0,
    )


@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    key_data: APIKeyRequest,
    current_user: CurrentUser,
    db: DatabaseSession,
    _csrf: CSRFToken,
) -> APIKeyResponse:
    """
    Create a new API key for authentication.

    The API key is only shown once during creation.
    Store it securely as it cannot be retrieved later.
    """
    # Generate API key
    plain_key, hashed_key = generate_api_key()

    # Calculate expiration
    expires_at = None
    if key_data.expires_days:
        expires_at = datetime.now(UTC) + timedelta(days=key_data.expires_days)

    # Create API key record
    api_key = APIKey(
        name=key_data.name,
        description=key_data.description,
        key_hash=hashed_key,
        created_by_user_id=current_user.id,
        expires_at=expires_at,
        created_at=datetime.now(UTC),
    )

    # Set scopes using the property setter (handles JSON serialization)
    api_key.scopes = key_data.scopes if key_data.scopes else ["admin"]

    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    # Safe logging
    safe_key_name = sanitize_for_logging(api_key.name)
    safe_username = sanitize_for_logging(current_user.username)
    logger.info(f"API key '{safe_key_name}' created by user {safe_username}")

    return APIKeyResponse(
        api_key=plain_key,
        key_id=api_key.id,
        name=api_key.name,
        created_at=api_key.created_at,
        expires_at=api_key.expires_at,
    )


@router.get("/api-keys")
async def list_api_keys(
    current_user: CurrentUser,
    db: DatabaseSession,
) -> list[dict]:
    """
    List API keys for current user.

    Note: Never returns actual keys, only metadata.
    """
    stmt = select(APIKey).where(
        APIKey.created_by_user_id == current_user.id,
        APIKey.is_active == True,
    )
    result = await db.execute(stmt)
    keys = result.scalars().all()

    return [
        {
            "id": key.id,
            "name": key.name,
            "description": key.description,
            "created_at": key.created_at,
            "expires_at": key.expires_at,
            "last_used_at": key.last_used_at,
            "usage_count": key.usage_count or 0,
            "scopes": key.scopes,  # Uses the property to get list
        }
        for key in keys
    ]


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: int,
    current_user: CurrentUser,
    db: DatabaseSession,
    _csrf: CSRFToken,
) -> dict:
    """
    Revoke an API key.
    """
    # Get API key
    api_key = await db.get(APIKey, key_id)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    # Check ownership (admins can revoke any key)
    if not current_user.is_admin and api_key.created_by_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot revoke this API key",
        )

    # Revoke key using the model's method
    api_key.revoke()
    await db.commit()

    # Safe logging
    safe_key_name = sanitize_for_logging(api_key.name)
    safe_username = sanitize_for_logging(current_user.username)
    logger.info(f"API key '{safe_key_name}' revoked by user {safe_username}")

    return {"message": "API key revoked successfully"}


@router.post("/session/refresh")
async def refresh_session(
    response: Response,
    session: SessionData | None = Depends(get_current_session),
) -> dict:
    """
    Refresh current session to extend expiration.
    """
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No active session",
        )

    auth_manager = get_auth_manager()
    refreshed_session = auth_manager.session_manager.refresh_session(session.session_id)

    if not refreshed_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to refresh session",
        )

    # Update cookie expiration
    settings = get_settings()
    response.set_cookie(
        key="harbor_session",  # pragma: allowlist secret
        value=refreshed_session.session_id,
        max_age=settings.security.session_timeout_hours * 3600,
        httponly=True,
        secure=settings.security.require_https,
        samesite="lax",
    )

    logger.info(f"Session refreshed for user (session: {session.session_id[:8]}...)")

    return {
        "message": "Session refreshed",
        "expires_at": refreshed_session.expires_at,
    }
