# app/db/config.py
"""
Harbor Database Configuration

Database configuration and connection management for Harbor.
Supports SQLite (home lab) and PostgreSQL (production).
"""

import os
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool, QueuePool, StaticPool

from app.config import DatabaseType, DeploymentProfile, get_settings
from app.utils.logging import get_logger


logger = get_logger(__name__)


# =============================================================================
# Database Configuration Class
# =============================================================================


class DatabaseConfig:
    """Database configuration management"""

    def __init__(
        self,
        deployment_profile: DeploymentProfile,
        database_type: DatabaseType,
        database_url: str | None = None,
        sqlite_path: Path | None = None,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30,
    ):
        self.deployment_profile = deployment_profile
        self.database_type = database_type
        self.database_url = database_url
        self.sqlite_path = sqlite_path
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self._engine: AsyncEngine | None = None

    def get_database_url(self) -> str:
        """Get the appropriate database URL"""
        # If explicit URL is provided, use it
        if self.database_url:
            return self.database_url

        # For SQLite, build the URL from path
        if self.database_type == DatabaseType.SQLITE:
            if self.sqlite_path:
                # Ensure parent directory exists
                self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
                return f"sqlite+aiosqlite:///{self.sqlite_path}"
            else:
                # Default SQLite path
                data_dir = Path(os.getenv("HARBOR_DATA_DIR", "data"))
                data_dir.mkdir(parents=True, exist_ok=True)
                db_path = data_dir / "harbor.db"
                return f"sqlite+aiosqlite:///{db_path}"

        # For PostgreSQL, require explicit URL
        if self.database_type == DatabaseType.POSTGRESQL:
            raise ValueError(
                "PostgreSQL selected but no DATABASE_URL provided. "
                "Please set DATABASE_URL environment variable."
            )

        raise ValueError(f"Unsupported database type: {self.database_type}")

    def get_pool_class(self) -> type:
        """Get appropriate connection pool class based on database type"""
        if self.database_type == DatabaseType.SQLITE:
            # SQLite doesn't support concurrent writes, use StaticPool
            return StaticPool
        elif self.deployment_profile == DeploymentProfile.DEVELOPMENT:
            # Development can use NullPool for easier debugging
            return NullPool
        else:
            # Production uses QueuePool for connection pooling
            return QueuePool

    def get_connect_args(self) -> dict[str, Any]:
        """Get database-specific connection arguments"""
        if self.database_type == DatabaseType.SQLITE:
            return {
                "check_same_thread": False,  # Allow multi-threading
                "timeout": 30.0,  # Connection timeout in seconds
            }
        else:
            # PostgreSQL connect args
            return {
                "server_settings": {
                    "application_name": "harbor",
                    "jit": "off",  # Disable JIT for more predictable performance
                },
                "command_timeout": 60,
            }

    def get_engine_kwargs(self) -> dict[str, Any]:
        """Get engine configuration kwargs"""
        pool_class = self.get_pool_class()
        connect_args = self.get_connect_args()

        kwargs = {
            "poolclass": pool_class,
            "connect_args": connect_args,
            "echo": self.deployment_profile == DeploymentProfile.DEVELOPMENT,
        }

        # Add pool configuration for appropriate pool types
        if pool_class == QueuePool:
            kwargs.update(
                {
                    "pool_size": self.pool_size,
                    "max_overflow": self.max_overflow,
                    "pool_timeout": self.pool_timeout,
                    "pool_recycle": 3600,  # Recycle connections after 1 hour
                    "pool_pre_ping": True,  # Test connections before using
                }
            )

        return kwargs

    async def create_engine(self) -> AsyncEngine:
        """Create and configure async database engine"""
        if self._engine is None:
            db_url = self.get_database_url()
            engine_kwargs = self.get_engine_kwargs()

            logger.info(
                f"Creating database engine for {self.database_type.value} "
                f"(profile: {self.deployment_profile.value})"
            )

            self._engine = create_async_engine(db_url, **engine_kwargs)

            # Log connection info (without credentials)
            safe_url = db_url.split("://")[0] + "://***"
            logger.debug(f"Database URL: {safe_url}")

        return self._engine

    async def dispose_engine(self) -> None:
        """Dispose of the database engine and close all connections"""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            logger.debug("Database engine disposed")


# =============================================================================
# Global Configuration Management
# =============================================================================

# Global database configuration instance
_database_config: DatabaseConfig | None = None
_engine: AsyncEngine | None = None


def get_database_config() -> DatabaseConfig:
    """Get database configuration instance"""
    global _database_config

    if _database_config is None:
        settings = get_settings()
        _database_config = DatabaseConfig(
            deployment_profile=settings.deployment_profile,
            database_type=settings.database.database_type,
            database_url=settings.database.database_url,
            sqlite_path=settings.database.sqlite_path,
            pool_size=settings.database.pool_size,
            max_overflow=settings.database.max_overflow,
            pool_timeout=settings.database.pool_timeout,
        )

        logger.debug(
            f"Created database config for {settings.database.database_type.value} "
            f"(profile: {settings.deployment_profile.value})"
        )

    return _database_config


async def get_engine() -> AsyncEngine:
    """Get or create async database engine"""
    global _engine

    if _engine is None:
        config = get_database_config()
        _engine = await config.create_engine()

    return _engine


async def dispose_engine() -> None:
    """Dispose of the global database engine"""
    global _engine

    if _engine is not None:
        await _engine.dispose()
        _engine = None
        logger.debug("Global database engine disposed")


def reset_database_config() -> None:
    """Reset database configuration (mainly for testing)"""
    global _database_config, _engine

    if _engine is not None:
        logger.warning(
            "Resetting database config with active engine - engine will be orphaned"
        )

    _database_config = None
    _engine = None
    logger.debug("Database configuration reset")


# =============================================================================
# Database URL Builders
# =============================================================================


def build_sqlite_url(path: Path | str | None = None) -> str:
    """Build SQLite connection URL"""
    if path is None:
        settings = get_settings()
        path = settings.data_dir / "harbor.db"

    if isinstance(path, str):
        path = Path(path)

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    return f"sqlite+aiosqlite:///{path}"


def build_postgresql_url(
    user: str,
    password: str,
    host: str,
    port: int,
    database: str,
    **kwargs: Any,
) -> str:
    """Build PostgreSQL connection URL"""
    base_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"

    if kwargs:
        # Add query parameters
        params = "&".join(f"{k}={v}" for k, v in kwargs.items())
        return f"{base_url}?{params}"

    return base_url


# =============================================================================
# Database Information Functions
# =============================================================================


def get_database_info() -> dict[str, Any]:
    """Get current database configuration information"""
    try:
        config = get_database_config()
        settings = get_settings()

        # Explicitly declare the type to accept Any values
        info: dict[str, Any] = {
            "deployment_profile": settings.deployment_profile.value,
            "database_type": config.database_type.value,
            "pool_size": config.pool_size,
            "max_overflow": config.max_overflow,
            "pool_timeout": config.pool_timeout,
        }

        # Add database-specific info
        if config.database_type == DatabaseType.SQLITE:
            if config.sqlite_path:
                info["database_path"] = str(config.sqlite_path)
                if config.sqlite_path.exists():
                    size_bytes = config.sqlite_path.stat().st_size
                    # Now this will work without issues
                    info["database_size_mb"] = round(size_bytes / (1024 * 1024), 2)
        else:
            # Mask credentials in URL
            safe_url = config.get_database_url().split("://")[0] + "://***"
            info["database_url"] = safe_url

        return info

    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        return {"error": str(e)}


def is_sqlite() -> bool:
    """Check if using SQLite database"""
    config = get_database_config()
    return config.database_type == DatabaseType.SQLITE


def is_postgresql() -> bool:
    """Check if using PostgreSQL database"""
    config = get_database_config()
    return config.database_type == DatabaseType.POSTGRESQL


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "DatabaseConfig",
    "build_postgresql_url",
    "build_sqlite_url",
    "dispose_engine",
    "get_database_config",
    "get_database_info",
    "get_engine",
    "is_postgresql",
    "is_sqlite",
    "reset_database_config",
]
