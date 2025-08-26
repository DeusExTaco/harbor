# app/db/init.py
"""
Harbor Database Initialization

Database setup, table creation, and initial data seeding for
first-time Harbor deployment.
"""

import os
import secrets
import string
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import DeploymentProfile, get_settings
from app.db.base import Base, import_all_models
from app.db.config import get_engine, is_sqlite
from app.db.session import get_async_session, initialize_session_manager
from app.utils.logging import get_logger


logger = get_logger(__name__)


async def create_tables(engine: AsyncEngine) -> None:
    """
    Create all database tables.

    Args:
        engine: AsyncEngine instance
    """
    # Import all models to ensure they're registered
    import_all_models()

    async with engine.begin() as conn:
        # Create all tables from models
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables created successfully")


async def drop_tables(engine: AsyncEngine) -> None:
    """
    Drop all database tables (DANGEROUS!).

    Args:
        engine: AsyncEngine instance
    """
    async with engine.begin() as conn:
        # Drop all tables
        await conn.run_sync(Base.metadata.drop_all)

    logger.warning("All database tables dropped")


async def initialize_sqlite_settings(engine: AsyncEngine) -> None:
    """
    Initialize SQLite-specific settings and optimizations.

    Args:
        engine: AsyncEngine instance
    """
    if not str(engine.url).startswith("sqlite"):
        return

    async with engine.begin() as conn:
        # Enable foreign key constraints
        await conn.execute(text("PRAGMA foreign_keys = ON"))

        # Set WAL mode for better concurrency
        await conn.execute(text("PRAGMA journal_mode = WAL"))

        # Set synchronous mode for balance of safety and performance
        await conn.execute(text("PRAGMA synchronous = NORMAL"))

        # Optimize cache size (in pages, negative means KB)
        await conn.execute(text("PRAGMA cache_size = -64000"))  # 64MB cache

        # Set busy timeout for better concurrency
        await conn.execute(text("PRAGMA busy_timeout = 30000"))  # 30 seconds

        # Enable automatic checkpointing
        await conn.execute(text("PRAGMA wal_autocheckpoint = 1000"))

    logger.info("SQLite optimization settings applied")


async def seed_initial_data() -> str | None:
    """
    Seed initial data for first-time setup.

    Returns:
        Admin password if created, None otherwise
    """
    # Initialize the session manager first
    await initialize_session_manager()

    admin_password = None

    try:
        async with get_async_session() as session:
            settings = get_settings()

            # Import models
            from app.db.models.settings import SystemSettings

            # Check if system settings exist
            existing_settings = await session.get(SystemSettings, 1)
            if not existing_settings:
                # Create initial system settings
                system_settings = SystemSettings(id=1)
                system_settings.apply_profile_defaults(settings.deployment_profile)

                session.add(system_settings)
                await session.commit()

                logger.info(
                    f"Created initial system settings for {settings.deployment_profile.value} profile"
                )

            # In home lab mode, create default admin user if needed
            if settings.deployment_profile == DeploymentProfile.HOMELAB:
                from sqlalchemy import select

                from app.db.models.user import User

                # Check if any users exist
                result = await session.execute(select(User))
                users = result.scalars().all()

                if not users:
                    # Generate secure password
                    alphabet = string.ascii_letters + string.digits
                    admin_password = "".join(
                        secrets.choice(alphabet) for _ in range(16)
                    )

                    # Create admin user (password will be hashed by the model)
                    admin = User(
                        username="admin",
                        display_name="Administrator",
                        email=None,
                        is_admin=True,
                        is_active=True,
                    )
                    admin.set_password(admin_password)

                    session.add(admin)
                    await session.commit()

                    logger.info("Created default admin user")

            # Add default Docker Hub registry
            from sqlalchemy import select

            from app.db.models.registry import Registry

            result = await session.execute(
                select(Registry).where(Registry.name == "docker.io")
            )
            existing_docker_hub = result.scalar_one_or_none()

            if not existing_docker_hub:
                new_registry = Registry(
                    name="docker.io",
                    endpoint="https://registry-1.docker.io",
                    registry_type="docker",
                    is_default=True,
                    is_active=True,
                )
                session.add(new_registry)
                await session.commit()

                logger.info("Added Docker Hub as default registry")

            logger.info("Initial data seeding completed")
            return admin_password

    except Exception as e:
        logger.error(f"Failed to seed initial data: {e}", exc_info=True)
        raise


async def check_database_health(engine: AsyncEngine | None = None) -> bool:
    """
    Check database connectivity and basic health.

    Args:
        engine: Optional AsyncEngine instance (will create if not provided)

    Returns:
        True if database is healthy
    """
    try:
        if engine is None:
            engine = await get_engine()

        async with engine.begin() as conn:
            # Test basic connectivity
            await conn.execute(text("SELECT 1"))

            # Check if tables exist
            if is_sqlite():
                result = await conn.execute(
                    text(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
                    )
                )
            else:
                result = await conn.execute(
                    text(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema='public' AND table_name='users'"
                    )
                )

            table_exists = result.scalar() is not None

        if table_exists:
            logger.info("Database health check passed - tables exist")
        else:
            logger.info("Database health check passed - no tables yet")

        return True

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


async def create_backup_directory() -> Path:
    """
    Create backup directory for home lab deployments.

    Returns:
        Path to backup directory
    """
    settings = get_settings()

    data_dir = Path(os.getenv("HARBOR_DATA_DIR", "data"))
    backup_dir = data_dir / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Backup directory ready: {backup_dir}")
    return backup_dir


async def initialize_database(force_recreate: bool = False) -> tuple[bool, str | None]:
    """
    Initialize database with tables and initial data.

    Args:
        force_recreate: If True, drop and recreate all tables

    Returns:
        Tuple of (success: bool, admin_password: Optional[str])
    """
    admin_password = None

    try:
        logger.info("Starting database initialization...")

        # Get database engine
        engine = await get_engine()

        # Check current database state
        if not force_recreate:
            healthy = await check_database_health(engine)
            if healthy:
                # Check if tables exist
                async with engine.begin() as conn:
                    if is_sqlite():
                        result = await conn.execute(
                            text(
                                "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
                            )
                        )
                    else:
                        result = await conn.execute(
                            text(
                                "SELECT COUNT(*) FROM information_schema.tables "
                                "WHERE table_schema='public'"
                            )
                        )

                    table_count = result.scalar() or 0

                    if table_count > 0:
                        logger.info(
                            f"Database already initialized with {table_count} tables"
                        )
                        return True, None

        # Initialize SQLite settings if needed
        await initialize_sqlite_settings(engine)

        # Drop tables if force recreate
        if force_recreate:
            await drop_tables(engine)

        # Create tables
        await create_tables(engine)

        # Seed initial data
        admin_password = await seed_initial_data()

        # Create backup directory for home lab
        if get_settings().deployment_profile == DeploymentProfile.HOMELAB:
            await create_backup_directory()

        # Final health check
        healthy = await check_database_health(engine)

        if healthy:
            logger.info("Database initialization completed successfully")
            if admin_password:
                logger.info("=" * 60)
                logger.info("IMPORTANT: Save these credentials!")
                logger.info("Admin Username: admin")
                logger.info(f"Admin Password: {admin_password}")
                logger.info("=" * 60)
        else:
            logger.error("Database initialization failed health check")

        return healthy, admin_password

    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        return False, None


async def reset_database() -> tuple[bool, str | None]:
    """
    Reset database - drop all tables and recreate (DANGEROUS!).

    Returns:
        Tuple of (success: bool, admin_password: Optional[str])
    """
    settings = get_settings()

    if settings.deployment_profile == DeploymentProfile.PRODUCTION:
        logger.error("Cannot reset production database!")
        raise ValueError("Cannot reset production database!")

    logger.warning("Resetting database - all data will be lost!")

    success, admin_password = await initialize_database(force_recreate=True)

    if success:
        logger.warning("Database reset completed")
    else:
        logger.error("Database reset failed")

    return success, admin_password


# Convenience functions
async def ensure_database_ready() -> bool:
    """
    Ensure database is ready for use (called during app startup).

    Returns:
        True if database is ready
    """
    success, _ = await initialize_database(force_recreate=False)
    return success


async def get_database_info() -> dict[str, Any]:
    """
    Get database information and statistics.

    Returns:
        Dictionary containing database information
    """
    try:
        engine = await get_engine()

        async with engine.begin() as conn:
            # Get basic info with explicit typing
            info: dict[str, Any] = {
                "dialect": engine.dialect.name,
                "driver": engine.dialect.driver,
                "server_version": None,
                "table_count": 0,
                "size_mb": None,
                "status": "connected",
            }

            # Get table count and size based on database type
            if is_sqlite():
                # Table count
                result = await conn.execute(
                    text("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                )
                info["table_count"] = result.scalar() or 0

                # Database file size
                if engine.url.database and os.path.exists(engine.url.database):
                    size_bytes = os.path.getsize(engine.url.database)
                    info["size_mb"] = round(size_bytes / (1024 * 1024), 2)

                # SQLite version
                result = await conn.execute(text("SELECT sqlite_version()"))
                info["server_version"] = result.scalar()

            else:  # PostgreSQL
                # Table count
                result = await conn.execute(
                    text(
                        "SELECT COUNT(*) FROM information_schema.tables "
                        "WHERE table_schema='public'"
                    )
                )
                info["table_count"] = result.scalar() or 0

                # Database size
                result = await conn.execute(
                    text("SELECT pg_database_size(current_database())")
                )
                size_bytes = result.scalar() or 0
                info["size_mb"] = round(size_bytes / (1024 * 1024), 2)

                # PostgreSQL version
                result = await conn.execute(text("SELECT version()"))
                version_str = result.scalar()
                if version_str:
                    # Extract version number from string
                    import re

                    match = re.search(r"PostgreSQL (\d+\.\d+)", version_str)
                    if match:
                        info["server_version"] = match.group(1)

            return info

    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        return {"error": "Unable to retrieve database information", "status": "error"}


__all__ = [
    "check_database_health",
    "create_tables",
    "drop_tables",
    "ensure_database_ready",
    "get_database_info",
    "initialize_database",
    "reset_database",
    "seed_initial_data",
]
