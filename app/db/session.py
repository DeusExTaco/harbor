# app/db/session.py
"""
Harbor Database Session Management - FIXED TYPE ANNOTATIONS

Database session management with proper typing and async context management.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.config import get_engine
from app.utils.logging import get_logger


logger = get_logger(__name__)


class DatabaseSessionManager:
    """Database session lifecycle manager with proper typing"""

    def __init__(self) -> None:
        self._session_factory: async_sessionmaker[AsyncSession] | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the session manager"""
        if not self._initialized:
            engine = await get_engine()
            self._session_factory = async_sessionmaker(
                engine,
                class_=AsyncSession,
                autoflush=False,
                autocommit=False,
                expire_on_commit=False,
            )
            self._initialized = True
            logger.debug("Database session manager initialized")

    def get_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get the session factory"""
        if not self._initialized or self._session_factory is None:
            raise RuntimeError(
                "Session manager not initialized. Call initialize() first."
            )
        return self._session_factory

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession]:
        """Get a database session with proper cleanup"""
        if not self._initialized or self._session_factory is None:
            raise RuntimeError(
                "Session manager not initialized. Call initialize() first."
            )

        async with self._session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def close(self) -> None:
        """Close the session manager"""
        if self._session_factory is not None:
            # Close the engine which will close all sessions
            engine = await get_engine()
            await engine.dispose()
            logger.debug("Database session manager closed")


# Global session manager
_session_manager: DatabaseSessionManager | None = None


def get_session_manager() -> DatabaseSessionManager:
    """Get the global session manager (singleton)"""
    global _session_manager
    if _session_manager is None:
        _session_manager = DatabaseSessionManager()
    return _session_manager


# Context manager for getting sessions
@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession]:
    """Get an async database session with proper cleanup"""
    session_manager = get_session_manager()
    async with session_manager.session() as session:
        yield session


# Alias for compatibility
get_session = get_async_session


# Convenience functions for session management
async def initialize_session_manager() -> None:
    """Initialize the global session manager"""
    session_manager = get_session_manager()
    await session_manager.initialize()


async def close_session_manager() -> None:
    """Close the global session manager"""
    if _session_manager is not None:
        await _session_manager.close()
