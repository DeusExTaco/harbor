# app/db/session.py
"""
Harbor Database Session Management

Database session management with async context managers and dependency injection
for FastAPI endpoints.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.db.config import dispose_engine, get_engine
from app.utils.logging import get_logger


logger = get_logger(__name__)


class DatabaseSessionManager:
    """
    Database session lifecycle manager.

    Manages session factory creation and provides context managers
    for database sessions with proper transaction handling.
    """

    def __init__(self) -> None:
        """Initialize session manager."""
        self._session_factory: async_sessionmaker[AsyncSession] | None = None
        self._engine: AsyncEngine | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize the session manager.

        Creates the session factory with appropriate configuration.
        """
        if not self._initialized:
            self._engine = await get_engine()
            self._session_factory = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                autoflush=False,
                autocommit=False,
                expire_on_commit=False,
            )
            self._initialized = True
            logger.debug("Database session manager initialized")

    def get_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """
        Get the session factory.

        Returns:
            Async session factory

        Raises:
            RuntimeError: If session manager not initialized
        """
        if not self._initialized or self._session_factory is None:
            raise RuntimeError(
                "Session manager not initialized. Call initialize() first."
            )
        return self._session_factory

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession]:
        """
        Get a database session with proper cleanup.

        Yields:
            AsyncSession instance

        Raises:
            RuntimeError: If session manager not initialized
        """
        if not self._initialized or self._session_factory is None:
            raise RuntimeError(
                "Session manager not initialized. Call initialize() first."
            )

        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[AsyncSession]:
        """
        Get a database session with explicit transaction management.

        Yields:
            AsyncSession instance
        """
        async with self.session() as session:
            async with session.begin():
                yield session

    async def close(self) -> None:
        """Close the session manager and dispose of the engine."""
        if self._engine is not None:
            await dispose_engine()
            self._engine = None
            self._session_factory = None
            self._initialized = False
            logger.debug("Database session manager closed")


# Global session manager (singleton)
_session_manager: DatabaseSessionManager | None = None


def get_session_manager() -> DatabaseSessionManager:
    """
    Get the global session manager (singleton).

    Returns:
        DatabaseSessionManager instance
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = DatabaseSessionManager()
    return _session_manager


# Context manager for getting sessions
@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession]:
    """
    Get an async database session with proper cleanup.

    This is the primary way to get a database session outside
    of FastAPI dependency injection.

    Yields:
        AsyncSession instance

    Examples:
        ```python
        async with get_async_session() as session:
            result = await session.execute(select(User).where(User.id == 1))
            user = result.scalar_one_or_none()
        ```
    """
    session_manager = get_session_manager()

    # Ensure manager is initialized
    if not session_manager._initialized:
        await session_manager.initialize()

    async with session_manager.session() as session:
        yield session


# Alias for compatibility
get_session = get_async_session


# FastAPI dependency for getting database sessions
async def get_db() -> AsyncGenerator[AsyncSession]:
    """
    Dependency injection for FastAPI endpoints.

    Provides an async database session that is automatically
    committed on success and rolled back on error.

    Yields:
        AsyncSession instance

    Examples:
        ```python
        @router.get("/containers")
        async def get_containers(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Container))
            return result.scalars().all()
        ```
    """
    async with get_async_session() as session:
        yield session


# Convenience functions for session management
async def initialize_session_manager() -> None:
    """Initialize the global session manager."""
    session_manager = get_session_manager()
    await session_manager.initialize()


async def close_session_manager() -> None:
    """Close the global session manager."""
    if _session_manager is not None:
        await _session_manager.close()


def reset_session_manager() -> None:
    """Reset the session manager (mainly for testing)."""
    global _session_manager
    _session_manager = None
    logger.debug("Session manager reset")


# Database transaction helper
@asynccontextmanager
async def database_transaction() -> AsyncGenerator[AsyncSession]:
    """
    Execute operations within a database transaction.

    Yields:
        AsyncSession instance with active transaction

    Examples:
        ```python
        async with database_transaction() as session:
            user = User(username="test")
            session.add(user)
            # Transaction commits on successful exit
        ```
    """
    session_manager = get_session_manager()

    # Ensure manager is initialized
    if not session_manager._initialized:
        await session_manager.initialize()

    async with session_manager.transaction() as session:
        yield session


# Testing utilities
async def test_database_connection() -> bool:
    """
    Test database connectivity.

    Returns:
        True if database is accessible
    """
    try:
        async with get_async_session() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False


# Export all public functions
__all__ = [
    "DatabaseSessionManager",
    "close_session_manager",
    "database_transaction",
    "get_async_session",
    "get_db",
    "get_session",
    "get_session_manager",
    "initialize_session_manager",
    "reset_session_manager",
    "test_database_connection",
]
