# app/db/repositories/user.py
"""
Harbor User Repository

User-specific database operations with authentication support
and relationship management.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.user import User
from app.db.repositories.base import PaginatedRepository
from app.utils.logging import get_logger


logger = get_logger(__name__)


class UserRepository(PaginatedRepository[User]):
    """Repository for user operations"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_username(self, username: str) -> User | None:
        """Get user by username"""
        stmt = select(User).where(User.username == username)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address"""
        if not email:
            return None

        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_api_keys(self, user_id: int) -> User | None:
        """Get user with API keys loaded"""
        stmt = (
            select(User).options(selectinload(User.api_keys)).where(User.id == user_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def username_exists(
        self, username: str, exclude_user_id: int | None = None
    ) -> bool:
        """Check if username exists (optionally excluding a specific user)"""
        stmt = select(User.id).where(User.username == username)

        if exclude_user_id:
            stmt = stmt.where(User.id != exclude_user_id)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def email_exists(
        self, email: str, exclude_user_id: int | None = None
    ) -> bool:
        """Check if email exists (optionally excluding a specific user)"""
        if not email:
            return False

        stmt = select(User.id).where(User.email == email)

        if exclude_user_id:
            stmt = stmt.where(User.id != exclude_user_id)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_active_users(self) -> list[User]:
        """Get all active users"""
        return await self.find_by(is_active=True)

    async def get_admin_users(self) -> list[User]:
        """Get all admin users"""
        return await self.find_by(is_admin=True, is_active=True)

    async def create_user(
        self,
        username: str,
        password_hash: str,
        email: str | None = None,
        display_name: str | None = None,
        is_admin: bool = False,
        timezone: str = "UTC",
    ) -> User:
        """
        Create a new user with validation
        """
        # Validate username uniqueness
        if await self.username_exists(username):
            raise ValueError(f"Username '{username}' already exists")

        # Validate email uniqueness if provided
        if email and await self.email_exists(email):
            raise ValueError(f"Email '{email}' already exists")

        # Use create_and_flush when we need the ID for logging
        user = await self.create_and_flush(
            username=username,
            password_hash=password_hash,
            email=email,
            display_name=display_name or username,
            is_admin=is_admin,
            timezone=timezone,
        )

        logger.info(f"Created user: {username} (id: {user.id}, admin: {is_admin})")
        return user

    async def create_user_no_flush(
        self,
        username: str,
        password_hash: str,
        email: str | None = None,
        display_name: str | None = None,
        is_admin: bool = False,
        timezone: str = "UTC",
    ) -> User:
        """
        Create a new user without flushing (for testing rollback scenarios)
        """
        # Validate username uniqueness
        if await self.username_exists(username):
            raise ValueError(f"Username '{username}' already exists")

        # Validate email uniqueness if provided
        if email and await self.email_exists(email):
            raise ValueError(f"Email '{email}' already exists")

        # Use regular create (no flush) - user won't have ID until commit
        user = await self.create(
            username=username,
            password_hash=password_hash,
            email=email,
            display_name=display_name or username,
            is_admin=is_admin,
            timezone=timezone,
        )

        logger.info(f"Added user to session: {username} (admin: {is_admin})")
        return user

    async def update_password(self, user_id: int, password_hash: str) -> User | None:
        """Update user password"""
        user = await self.update_by_id(user_id, password_hash=password_hash)

        if user:
            logger.info(f"Updated password for user: {user.username} (id: {user_id})")

        return user

    async def update_profile(
        self,
        user_id: int,
        display_name: str | None = None,
        email: str | None = None,
        timezone: str | None = None,
    ) -> User | None:
        """Update user profile information"""
        updates = {}
        if display_name is not None:
            updates["display_name"] = display_name
        if email is not None:
            # Validate email uniqueness
            if email and await self.email_exists(email, exclude_user_id=user_id):
                raise ValueError(f"Email '{email}' already exists")
            updates["email"] = email
        if timezone is not None:
            updates["timezone"] = timezone

        if updates:
            user = await self.update_by_id(user_id, **updates)

            if user:
                logger.info(
                    f"Updated profile for user: {user.username} (id: {user_id})"
                )

            return user

        return await self.get_by_id(user_id)

    async def deactivate_user(self, user_id: int) -> User | None:
        """Deactivate user account"""
        user = await self.update_by_id(user_id, is_active=False)

        if user:
            logger.info(f"Deactivated user: {user.username} (id: {user_id})")

        return user

    async def activate_user(self, user_id: int) -> User | None:
        """Activate user account"""
        user = await self.update_by_id(user_id, is_active=True)

        if user:
            logger.info(f"Activated user: {user.username} (id: {user_id})")

        return user

    async def record_login(self, user_id: int) -> User | None:
        """Record successful login"""
        user = await self.get_by_id(user_id)

        if user:
            user.record_login()
            logger.debug(
                f"Recorded login for user: {user.username} (count: {user.login_count})"
            )

        return user

    async def search_users(
        self, query: str, page: int = 1, per_page: int = 20, active_only: bool = True
    ) -> Any:
        """Search users by username, display name, or email"""
        filters = {}
        if active_only:
            filters["is_active"] = True

        return await self.search_paginated(
            query=query,
            search_fields=["username", "display_name", "email"],
            page=page,
            per_page=per_page,
            **filters,
        )
