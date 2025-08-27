# app/db/config.py
"""
Harbor Database Configuration

Database connection configuration and engine management for both
SQLite (home lab) and PostgreSQL (enterprise) deployments.
"""

import os
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import DeploymentProfile, get_settings
from app.utils.logging import get_logger


logger = get_logger(__name__)

# Global engine instance (singleton)
_engine: AsyncEngine | None = None


class DatabaseConfig:
    """Database configuration for different deployment profiles"""

    def __init__(self):
        self.settings = get_settings()
        self.deployment_profile = self.settings.deployment_profile

    def get_database_url(self, async_driver: bool = True) -> str:
        """
        Get appropriate database URL for deployment profile.

        Args:
            async_driver: Whether to use async driver (default: True)

        Returns:
            Database connection URL
        """
        if self.deployment_profile == DeploymentProfile.HOMELAB:
            # SQLite for home lab - zero config
            data_dir = Path(os.getenv("HARBOR_DATA_DIR", "data"))
            data_dir.mkdir(parents=True, exist_ok=True)

            if async_driver:
                return f"sqlite+aiosqlite:///{data_dir}/harbor.db"
            else:
                return f"sqlite:///{data_dir}/harbor.db"

        elif self.deployment_profile == DeploymentProfile.PRODUCTION:
            # PostgreSQL for production - from environment
            db_url = os.getenv("DATABASE_URL")
            if not db_url:
                raise ValueError(
                    "DATABASE_URL environment variable required for production"
                )

            # Ensure async driver for PostgreSQL if requested
            if async_driver and "postgresql://" in db_url:
                db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
            elif not async_driver and "postgresql+asyncpg://" in db_url:
                db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

            return db_url

        elif self.deployment_profile == DeploymentProfile.DEVELOPMENT:
            # Development can use SQLite or PostgreSQL
            db_url = os.getenv(
                "DATABASE_URL", f"sqlite+aiosqlite:///{Path('data/harbor_dev.db')}"
            )

            # Ensure async driver consistency
            if async_driver:
                if "sqlite://" in db_url and "aiosqlite" not in db_url:
                    db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://")
                elif "postgresql://" in db_url and "asyncpg" not in db_url:
                    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
            else:
                if "sqlite+aiosqlite://" in db_url:
                    db_url = db_url.replace("sqlite+aiosqlite://", "sqlite://")
                elif "postgresql+asyncpg://" in db_url:
                    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

            return db_url

        else:
            # Default to SQLite for unknown profiles
            data_dir = Path(os.getenv("HARBOR_DATA_DIR", "data"))
            data_dir.mkdir(parents=True, exist_ok=True)

            if async_driver:
                return f"sqlite+aiosqlite:///{data_dir}/harbor.db"
            else:
                return f"sqlite:///{data_dir}/harbor.db"

    def get_connection_config(self) -> dict[str, Any]:
        """
        Get connection pool configuration based on database type.

        Returns:
            Connection pool configuration dict
        """
        database_url = self.get_database_url()

        # SQLite with StaticPool doesn't accept pool parameters
        if "sqlite" in database_url.lower():
            return {
                "poolclass": StaticPool,
                "connect_args": {
                    "check_same_thread": False,
                },
                "echo": False,
            }

        # PostgreSQL and other databases can use pool parameters
        if self.deployment_profile == DeploymentProfile.HOMELAB:
            return {
                "pool_size": 5,
                "max_overflow": 2,
                "pool_timeout": 30,
                "echo": False,
                "pool_pre_ping": True,
            }
        elif self.deployment_profile == DeploymentProfile.PRODUCTION:
            return {
                "pool_size": 20,
                "max_overflow": 10,
                "pool_timeout": 60,
                "echo": False,
                "pool_pre_ping": True,  # Verify connections before use in production
            }
        else:  # Development/staging
            return {
                "pool_size": 10,
                "max_overflow": 5,
                "pool_timeout": 30,
                "echo": False,
                "pool_pre_ping": True,
            }

    def is_sqlite(self) -> bool:
        """Check if using SQLite database."""
        url = self.get_database_url()
        return "sqlite" in url.lower()


# Module-level functions for backwards compatibility and convenience


def get_database_config() -> DatabaseConfig:
    """Get database configuration instance."""
    return DatabaseConfig()


def is_sqlite() -> bool:
    """
    Check if using SQLite database.

    Returns:
        True if using SQLite
    """
    config = get_database_config()
    return config.is_sqlite()


async def get_engine(force_new: bool = False) -> AsyncEngine:
    """
    Get or create async database engine (singleton).

    Args:
        force_new: Force creation of new engine

    Returns:
        AsyncEngine instance
    """
    global _engine

    if _engine is None or force_new:
        if _engine is not None:
            await _engine.dispose()

        config = get_database_config()
        database_url = config.get_database_url(async_driver=True)
        connection_config = config.get_connection_config()

        _engine = create_async_engine(database_url, **connection_config)

        logger.debug(f"Created database engine for {database_url.split('@')[0]}")

    return _engine


async def dispose_engine() -> None:
    """Dispose of the current engine and close all connections."""
    global _engine

    if _engine is not None:
        await _engine.dispose()
        _engine = None
        logger.debug("Database engine disposed")


async def test_database_connection() -> bool:
    """
    Test database connectivity.

    Returns:
        True if database is accessible
    """
    try:
        from sqlalchemy import text

        engine = await get_engine()
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))

        logger.info("Database connection test successful")
        return True

    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False


# Export all public functions and classes
__all__ = [
    "DatabaseConfig",
    "dispose_engine",
    "get_database_config",
    "get_engine",
    "is_sqlite",
    "test_database_connection",
]
