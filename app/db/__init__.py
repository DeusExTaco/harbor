# app/db/__init__.py
"""
Harbor Database Package

Database initialization, models, and utilities for Harbor Container Updater.
This module provides the core database functionality for M0 milestone.

FIXED: Removed unused imports to pass pre-commit checks
"""

from pathlib import Path

from sqlalchemy import text

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

        # Insert default data
        await _insert_default_data()

        logger.info("Database initialization completed successfully")
        return True

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


async def _insert_default_data() -> None:
    """Insert default system data"""
    try:
        async with get_async_session() as session:
            # Check if system settings exist
            settings = await session.get(SystemSettings, 1)
            if not settings:
                # Create default system settings
                default_settings = SystemSettings(id=1)
                session.add(default_settings)
                await session.commit()
                logger.info("Created default system settings")

    except Exception as e:
        logger.error(f"Failed to insert default data: {e}")
        raise


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

            return {
                "status": "healthy",
                "connection": "ok",
                "tables": "accessible",
                "system_settings": "found" if settings else "missing",
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

            info = {
                "dialect": dialect,
                "database_url": database_url,
                "table_count": table_count,
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
    "check_database_health",
    "get_database_info",
]
