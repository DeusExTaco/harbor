# app/db/init.py
"""
Harbor Database Initialization

Database setup, table creation, and initial data seeding for
first-time Harbor deployment.
"""

import os
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import DeploymentProfile, get_settings
from app.db.base import Base
from app.db.config import get_engine
from app.db.models.settings import SystemSettings
from app.db.session import get_async_session
from app.utils.logging import get_logger


logger = get_logger(__name__)


async def create_tables(engine: AsyncEngine) -> None:
    """Create all database tables"""
    async with engine.begin() as conn:
        # Create all tables from models
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables created successfully")


async def initialize_sqlite_settings(engine: AsyncEngine) -> None:
    """Initialize SQLite-specific settings and optimizations"""
    if not str(engine.url).startswith("sqlite"):
        return

    async with engine.begin() as conn:
        # Enable foreign key constraints
        await conn.execute(text("PRAGMA foreign_keys = ON"))

        # Set WAL mode for better concurrency
        await conn.execute(text("PRAGMA journal_mode = WAL"))

        # Set synchronous mode for balance of safety and performance
        await conn.execute(text("PRAGMA synchronous = NORMAL"))

        # Optimize cache size (in pages)
        await conn.execute(text("PRAGMA cache_size = -64000"))  # 64MB cache

        # Set busy timeout for better concurrency
        await conn.execute(text("PRAGMA busy_timeout = 30000"))  # 30 seconds

        # Enable automatic checkpointing
        await conn.execute(text("PRAGMA wal_autocheckpoint = 1000"))

    logger.info("SQLite optimization settings applied")


async def seed_initial_data() -> None:
    """Seed initial data for first-time setup"""
    # Initialize the session manager before trying to use it
    from app.db.session import get_session_manager

    session_manager = get_session_manager()
    await session_manager.initialize()

    try:
        async with get_async_session() as session:
            settings = get_settings()

            # Check if system settings exist
            existing_settings = await session.get(SystemSettings, 1)
            if not existing_settings:
                # Create initial system settings
                system_settings = SystemSettings(id=1)
                system_settings.apply_profile_defaults(settings.deployment_profile)

                session.add(system_settings)
                await session.commit()
                await session.refresh(system_settings)

                logger.info(
                    f"Created initial system settings for {settings.deployment_profile.value} profile"
                )

            # In home lab mode, check if we need to create an admin user
            if settings.deployment_profile == DeploymentProfile.HOMELAB:
                # Check if any users exist
                result = await session.execute(text("SELECT COUNT(*) FROM users"))
                user_count = result.scalar()

                if user_count == 0:
                    # No users exist - this will be handled by first-run setup
                    logger.info(
                        "No users found - first-run setup will create admin user"
                    )

            logger.info("Initial data seeding completed")

    except Exception as e:
        logger.error(f"Failed to seed initial data: {e}")
        raise


async def check_database_health(engine: AsyncEngine) -> bool:
    """Check database connectivity and basic health"""
    try:
        async with engine.begin() as conn:
            # Test basic connectivity
            await conn.execute(text("SELECT 1"))

            # Check if tables exist
            if str(engine.url).startswith("sqlite"):
                result = await conn.execute(
                    text(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
                    )
                )
            else:
                result = await conn.execute(
                    text(
                        "SELECT table_name FROM information_schema.tables WHERE table_name='users'"
                    )
                )

            table_exists = result.scalar() is not None

        logger.info("Database health check passed")
        return table_exists

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


async def create_backup_directory() -> None:
    """Create backup directory for home lab deployments"""
    settings = get_settings()

    if settings.deployment_profile == DeploymentProfile.HOMELAB:
        data_dir = Path(os.getenv("HARBOR_DATA_DIR", "data"))
        backup_dir = data_dir / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Created backup directory: {backup_dir}")


async def initialize_database(force_recreate: bool = False) -> bool:
    """
    Initialize database with tables and initial data

    Args:
        force_recreate: If True, drop and recreate all tables

    Returns:
        bool: True if initialization successful
    """
    try:
        logger.info("Starting database initialization...")

        # Get database engine
        engine = await get_engine()

        # Check if database already exists and is healthy
        if not force_recreate:
            tables_exist = await check_database_health(engine)
            if tables_exist:
                logger.info("Database already initialized and healthy")
                return True

        # Initialize SQLite settings if needed
        await initialize_sqlite_settings(engine)

        # Drop tables if force recreate
        if force_recreate:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            logger.info("Dropped existing database tables")

        # Create tables
        await create_tables(engine)

        # Seed initial data
        await seed_initial_data()

        # Create backup directory for home lab
        await create_backup_directory()

        # Final health check
        healthy = await check_database_health(engine)

        if healthy:
            logger.info("Database initialization completed successfully")
        else:
            logger.error("Database initialization failed health check")

        return healthy

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


async def reset_database() -> bool:
    """Reset database - drop all tables and recreate (DANGEROUS!)"""
    logger.warning("Resetting database - all data will be lost!")

    success = await initialize_database(force_recreate=True)

    if success:
        logger.warning("Database reset completed")
    else:
        logger.error("Database reset failed")

    return success


# Convenience functions for common operations
async def ensure_database_ready() -> bool:
    """Ensure database is ready for use (called during app startup)"""
    return await initialize_database(force_recreate=False)


async def get_database_info() -> dict[str, Any]:
    """Get database information for debugging/status"""
    try:
        engine = await get_engine()

        info: dict[str, Any] = {
            "url": str(engine.url).split("://", 1)[0] + "://***",  # Hide credentials
            "dialect": engine.dialect.name,
            "driver": engine.dialect.driver,
        }

        # Get table count
        async with engine.begin() as conn:
            if str(engine.url).startswith("sqlite"):
                result = await conn.execute(
                    text("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                )
            else:
                result = await conn.execute(
                    text("SELECT COUNT(*) FROM information_schema.tables")
                )

            info["table_count"] = result.scalar()

        # Get database size (SQLite only)
        if str(engine.url).startswith("sqlite"):
            db_path = str(engine.url).split(":///", 1)[1]
            if Path(db_path).exists():
                size_bytes = Path(db_path).stat().st_size
                size_mb: float = round(size_bytes / (1024 * 1024), 2)
                info["size_mb"] = size_mb  # Explicitly typed as float

        return info

    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        return {"error": str(e)}
