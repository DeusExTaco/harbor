# app/db/repositories/api_key.py
"""
Harbor API Key Repository

Database operations for API key management.
"""

from datetime import UTC, datetime

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.api_key import APIKey
from app.db.repositories.base import BaseRepository
from app.utils.logging import get_logger


logger = get_logger(__name__)


class APIKeyRepository(BaseRepository[APIKey]):
    """Repository for API key database operations."""

    def __init__(self, session: AsyncSession):
        """Initialize API key repository."""
        super().__init__(session, APIKey)

    async def get_by_hash(self, key_hash: str) -> APIKey | None:
        """
        Get API key by its hash.

        Args:
            key_hash: Hashed API key

        Returns:
            APIKey if found, None otherwise
        """
        stmt = select(APIKey).where(
            and_(
                APIKey.key_hash == key_hash,
                APIKey.is_active == True,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_key_hash(self, key_hash: str) -> APIKey | None:
        """
        Get API key by its hash (including inactive/expired).

        This method returns the key even if expired or inactive,
        allowing the caller to determine the specific rejection reason.

        Args:
            key_hash: Hashed API key

        Returns:
            APIKey if found, None otherwise
        """
        stmt = select(APIKey).where(APIKey.key_hash == key_hash)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_keys(
        self, user_id: int, include_inactive: bool = False
    ) -> list[APIKey]:
        """
        Get all API keys for a user.

        Args:
            user_id: User ID to get keys for
            include_inactive: Whether to include inactive keys

        Returns:
            List of API keys
        """
        stmt = select(APIKey).where(APIKey.created_by_user_id == user_id)

        if not include_inactive:
            stmt = stmt.where(APIKey.is_active == True)

        stmt = stmt.order_by(APIKey.created_at.desc())

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_user_keys(self, user_id: int, active_only: bool = True) -> int:
        """
        Count API keys for a user.

        Args:
            user_id: User ID
            active_only: Count only active keys

        Returns:
            Number of keys
        """
        filters = {"created_by_user_id": user_id}
        if active_only:
            filters["is_active"] = True

        return await self.count(**filters)

    async def cleanup_expired(self) -> int:
        """
        Deactivate expired API keys.

        Returns:
            Number of keys deactivated
        """
        now = datetime.now(UTC)
        stmt = select(APIKey).where(
            and_(
                APIKey.expires_at != None,
                APIKey.expires_at < now,
                APIKey.is_active == True,
            )
        )

        result = await self.session.execute(stmt)
        expired_keys = result.scalars().all()

        count = 0
        for key in expired_keys:
            key.is_active = False
            key.update_timestamp()
            count += 1
            logger.debug(f"Deactivated expired API key '{key.name}'")

        if count > 0:
            logger.info(f"Deactivated {count} expired API keys")

        return count

    async def record_usage(self, key_id: int, ip_address: str | None = None) -> bool:
        """
        Record API key usage.

        Args:
            key_id: API key ID
            ip_address: Client IP address

        Returns:
            True if updated successfully
        """
        api_key = await self.get_by_id(key_id)
        if not api_key:
            return False

        api_key.record_usage(ip_address)
        return True

    async def track_usage(self, api_key_id: int, ip_address: str | None = None) -> None:
        """
        Track API key usage.

        Args:
            api_key_id: API key ID
            ip_address: Client IP address
        """
        stmt = (
            update(APIKey)
            .where(APIKey.id == api_key_id)
            .values(
                usage_count=APIKey.usage_count + 1,
                last_used_at=datetime.now(UTC),
                last_used_ip=ip_address,
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_active_count(self) -> int:
        """Get count of all active API keys."""
        return await self.count(is_active=True)
