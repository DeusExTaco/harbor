# app/db/__init__.py
"""
Harbor Database Package

Database initialization, models, and utilities for Harbor Container Updater.
This module provides the core database functionality for M0 milestone.

FIXED: Removed unused imports to pass pre-commit checks
"""

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select, text

from app.auth.password import generate_password

# Import core database components
from app.db.base import Base
from app.db.config import get_engine
from app.db.models.api_key import APIKey as APIKey  # Explicit re-export
from app.db.models.settings import SystemSettings
from app.db.models.user import User as User  # Explicit re-export
from app.db.session import get_async_session
from app.utils.logging import get_logger


logger = get_logger(__name__)


# =============================================================================
# Database Initialization
# =============================================================================


async def initialize_database(force_recreate: bool = False) -> bool:
    """
    Initialize database with all tables and default data

    Args:
        force_recreate: If True, drop and recreate all tables

    Returns:
        bool: True if initialization successful
    """
    try:
        engine = await get_engine()  # Fix: await the coroutine

        if force_recreate:
            logger.info("Force recreating database tables")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)

        logger.info("Creating database tables")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Insert default data including admin user
        await _insert_default_data()

        logger.info("Database initialization completed successfully")
        return True

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


async def _insert_default_data() -> None:
    """Insert default system data and ensure admin user exists"""
    from app.auth.password import generate_password, hash_password
    from app.config import get_settings

    settings = get_settings()

    try:
        async with get_async_session() as session:
            # Check if system settings exist
            system_settings = await session.get(SystemSettings, 1)
            if not system_settings:
                # Create default system settings
                default_settings = SystemSettings(
                    id=1,
                    deployment_profile=settings.deployment_profile.value,
                    default_check_interval_seconds=86400,
                    default_update_time="03:00",
                    default_timezone="UTC",
                    enable_auto_discovery=True,
                    enable_simple_mode=True,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
                session.add(default_settings)
                await session.commit()
                logger.info("Created default system settings")

            # Check for admin user
            stmt = select(User).where(User.username == "admin")
            result = await session.execute(stmt)
            admin = result.scalar_one_or_none()

            if not admin:
                # Create admin user
                if settings.deployment_profile.value == "development":
                    # Use known password for development
                    password = "Harbor123!"  # pragma: allowlist secret # nosec B105 - Development only
                else:
                    # Generate secure password for production
                    password = generate_password(16)

                admin = User(
                    username="admin",
                    password_hash=hash_password(password),
                    email="admin@harbor.local",
                    display_name="Administrator",
                    is_admin=True,
                    is_active=True,
                    created_at=datetime.now(UTC),
                    login_count=0,
                    failed_login_count=0,
                )
                session.add(admin)
                await session.commit()

                logger.info("=" * 60)
                logger.info("IMPORTANT: Save these credentials!")
                logger.info("Admin Username: admin")
                logger.info(f"Admin Password: {password}")
                logger.info("=" * 60)

            elif settings.deployment_profile.value == "development":
                # For development, ensure admin has known password
                password = "Harbor123!"  # pragma: allowlist secret # nosec B105 - Development only
                admin.password_hash = hash_password(password)
                admin.is_active = True
                admin.failed_login_count = 0
                await session.commit()
                logger.info(f"Admin password set for development: {password}")

    except Exception as e:
        logger.error(f"Failed to insert default data: {e}")
        raise


async def ensure_admin_user() -> bool:
    """
    Ensure admin user exists with proper credentials
    Used during application startup

    Returns:
        bool: True if admin user is ready
    """
    from app.auth.password import hash_password, verify_password
    from app.config import get_settings

    settings = get_settings()

    try:
        async with get_async_session() as session:
            # Check for admin user
            stmt = select(User).where(User.username == "admin")
            result = await session.execute(stmt)
            admin = result.scalar_one_or_none()

            if not admin:
                logger.warning("Admin user not found - creating")

                # Create admin with development password
                password = (
                    "Harbor123!"
                    if settings.deployment_profile.value == "development"
                    else generate_password(16)
                )
                admin = User(
                    username="admin",
                    password_hash=hash_password(password),
                    email="admin@harbor.local",
                    display_name="Administrator",
                    is_admin=True,
                    is_active=True,
                    created_at=datetime.now(UTC),
                )
                session.add(admin)
                await session.commit()

                logger.info(f"Admin user created with password: {password}")
                return True

            # Verify admin is active
            if not admin.is_active:
                admin.is_active = True
                await session.commit()
                logger.info("Admin user activated")

            # In development, ensure password is known
            if settings.deployment_profile.value == "development":
                test_password = "Harbor123!"  # pragma: allowlist secret # nosec B105 - Development only
                if not verify_password(test_password, admin.password_hash):
                    admin.password_hash = hash_password(test_password)
                    await session.commit()
                    logger.info(
                        f"Admin password reset for development: {test_password}"
                    )

            return True

    except Exception as e:
        logger.error(f"Failed to ensure admin user: {e}")
        return False


# =============================================================================
# Database Health Check
# =============================================================================


async def check_database_health() -> dict:
    """
    Check database health and connectivity

    Returns:
        dict: Health check results
    """
    try:
        async with get_async_session() as session:
            # Test basic connectivity
            result = await session.execute(text("SELECT 1 as test"))
            test_value = result.scalar()

            if test_value != 1:
                return {
                    "status": "unhealthy",
                    "error": "Basic connectivity test failed",
                }

            # Test table access
            settings = await session.get(SystemSettings, 1)

            # Check for admin user
            stmt = select(User).where(User.username == "admin")
            result = await session.execute(stmt)
            admin = result.scalar_one_or_none()

            return {
                "status": "healthy",
                "connection": "ok",
                "tables": "accessible",
                "system_settings": "found" if settings else "missing",
                "admin_user": "found" if admin else "missing",
            }

    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


# =============================================================================
# Database Information
# =============================================================================


async def get_database_info() -> dict:
    """
    Get database information and statistics

    Returns:
        dict: Database information
    """
    try:
        engine = await get_engine()  # Fix: await the coroutine

        # Get basic connection info
        dialect = engine.dialect.name
        database_url = str(engine.url).split("://")[0] + "://***"  # Mask credentials

        async with get_async_session() as session:
            # Count tables
            if dialect == "sqlite":
                result = await session.execute(
                    text(
                        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                    )
                )
                table_count = result.scalar()

                # Get database size for SQLite
                try:
                    db_path = Path(str(engine.url).replace("sqlite:///", ""))
                    if db_path.exists():
                        size_bytes = db_path.stat().st_size
                        size_mb = round(size_bytes / (1024 * 1024), 2)
                    else:
                        size_mb = 0
                except Exception:
                    size_mb = None

            else:
                # PostgreSQL
                result = await session.execute(
                    text(
                        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
                    )
                )
                table_count = result.scalar()
                size_mb = None  # Not easily available for PostgreSQL

            # Count users
            user_stmt = select(User)
            user_result = await session.execute(user_stmt)
            user_count = len(user_result.scalars().all())

            info = {
                "dialect": dialect,
                "database_url": database_url,
                "table_count": table_count,
                "user_count": user_count,
                "status": "connected",
            }

            if size_mb is not None:
                info["size_mb"] = size_mb

            return info

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "dialect": "unknown",
            "table_count": 0,
            "user_count": 0,
        }


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    # Core components
    "Base",
    "get_engine",
    "get_async_session",
    # Models (explicit re-exports)
    "APIKey",
    "SystemSettings",
    "User",
    # Functions
    "initialize_database",
    "ensure_admin_user",
    "check_database_health",
    "get_database_info",
]
