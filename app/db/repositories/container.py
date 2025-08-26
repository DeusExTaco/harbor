# app/db/repositories/container.py
"""
Harbor Container Repository

Data access layer for container management operations.
Provides CRUD operations and business logic for container entities.

FIXED: Removed unused variable assignment to pass pre-commit checks
"""

from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.container import Container
from app.db.repositories.base import BaseRepository
from app.utils.logging import get_logger


logger = get_logger(__name__)


class SearchResult:
    """Container search result with pagination info"""

    def __init__(self, items: list[Container], total: int, page: int, per_page: int):
        self.items = items
        self.total = total
        self.page = page
        self.per_page = per_page
        self.pages = (total + per_page - 1) // per_page
        self.has_next = page < self.pages
        self.has_prev = page > 1


class ContainerRepository(BaseRepository[Container]):
    """Repository for container data operations"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Container)

    async def create_or_update_container(
        self,
        uid: str,
        docker_id: str,
        docker_name: str,
        image_repo: str,
        image_tag: str,
        image_ref: str,
        status: str,
        current_digest: str | None = None,
        **kwargs: Any,  # Add type annotation
    ) -> Container:
        """
        Create new container or update existing one

        Args:
            uid: Container UID (stable identifier)
            docker_id: Current Docker container ID
            docker_name: Container name
            image_repo: Image repository name
            image_tag: Image tag
            image_ref: Full image reference
            status: Container status
            current_digest: Current image digest
            **kwargs: Additional container attributes

        Returns:
            Container: Created or updated container
        """
        # Try to find existing container by UID
        existing = await self.get_by_uid(uid)

        if existing:
            # Update existing container
            existing.docker_id = docker_id
            existing.docker_name = docker_name
            existing.image_repo = image_repo
            existing.image_tag = image_tag
            existing.image_ref = image_ref
            existing.status = status
            existing.current_digest = current_digest
            existing.last_seen_at = func.now()

            # Update additional attributes
            for key, value in kwargs.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)

            logger.debug(f"Updated existing container: {docker_name} ({uid})")
            return existing
        else:
            # Create new container
            container = Container(
                uid=uid,
                docker_id=docker_id,
                docker_name=docker_name,
                image_repo=image_repo,
                image_tag=image_tag,
                image_ref=image_ref,
                status=status,
                current_digest=current_digest,
                **kwargs,
            )

            self.session.add(container)
            await self.session.flush()  # Get the ID

            logger.debug(f"Created new container: {docker_name} ({uid})")
            return container

    async def get_by_uid(self, uid: str) -> Container | None:
        """Get container by UID"""
        stmt = select(Container).where(Container.uid == uid)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_docker_id(self, docker_id: str) -> Container | None:
        """Get container by Docker ID"""
        stmt = select(Container).where(Container.docker_id == docker_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Container | None:
        """Get container by name"""
        stmt = select(Container).where(Container.docker_name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_managed_containers(self) -> list[Container]:
        """Get all managed containers"""
        stmt = select(Container).where(Container.managed == True)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_outdated_containers(self) -> list[Container]:
        """
        Get containers with available updates

        NOTE: This is a placeholder implementation for M0.
        M1 will implement actual registry comparison logic.
        """
        # FIXED: Removed unused stmt variable
        # TODO M1: Implement actual registry comparison
        # For now, return empty list - will be implemented in M1 milestone
        return []

    async def search_containers(
        self,
        query: str | None = None,
        status: str | None = None,
        managed: bool | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> SearchResult:
        """
        Search containers with filters and pagination

        Args:
            query: Search query for name/image
            status: Filter by status
            managed: Filter by managed status
            page: Page number (1-based)
            per_page: Items per page

        Returns:
            SearchResult: Paginated search results
        """
        # Build base query
        stmt = select(Container)

        # Apply filters
        conditions = []

        if query:
            conditions.append(
                or_(
                    Container.docker_name.ilike(f"%{query}%"),
                    Container.image_repo.ilike(f"%{query}%"),
                    Container.image_ref.ilike(f"%{query}%"),
                )
            )

        if status:
            conditions.append(Container.status == status)

        if managed is not None:
            conditions.append(Container.managed == managed)

        if conditions:
            stmt = stmt.where(*conditions)

        # Count total results
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar()

        # Apply pagination
        offset = (page - 1) * per_page
        stmt = stmt.offset(offset).limit(per_page)

        # Execute query
        result = await self.session.execute(stmt)
        containers = list(result.scalars().all())

        return SearchResult(containers, total, page, per_page)

    async def get_containers_with_policies(self) -> list[Container]:
        """Get all containers with their policies loaded"""
        stmt = select(Container).options(selectinload(Container.policy))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_container_status(self, uid: str, status: str) -> bool:
        """Update container status"""
        container = await self.get_by_uid(uid)
        if container:
            container.status = status
            container.last_seen_at = func.now()
            return True
        return False

    async def mark_container_updated(
        self, uid: str, new_digest: str | None = None
    ) -> bool:
        """Mark container as recently updated"""
        container = await self.get_by_uid(uid)
        if container:
            container.last_updated_at = func.now()
            if new_digest:
                container.current_digest = new_digest
            container.update_count += 1
            return True
        return False

    async def get_statistics(self) -> dict:
        """Get container statistics"""
        try:
            # Total containers
            total_stmt = select(func.count(Container.id))
            total_result = await self.session.execute(total_stmt)
            total = total_result.scalar()

            # Managed containers
            managed_stmt = select(func.count(Container.id)).where(
                Container.managed == True
            )
            managed_result = await self.session.execute(managed_stmt)
            managed = managed_result.scalar()

            # Running containers
            running_stmt = select(func.count(Container.id)).where(
                Container.status == "running"
            )
            running_result = await self.session.execute(running_stmt)
            running = running_result.scalar()

            # Stopped containers
            stopped_stmt = select(func.count(Container.id)).where(
                Container.status == "stopped"
            )
            stopped_result = await self.session.execute(stopped_stmt)
            stopped = stopped_result.scalar()

            return {
                "total_containers": total,
                "managed_containers": managed,
                "unmanaged_containers": total - managed,
                "running_containers": running,
                "stopped_containers": stopped,
                "outdated_containers": 0,  # TODO M1: Implement
            }

        except Exception as e:
            logger.error(f"Failed to get container statistics: {e}")
            return {
                "total_containers": 0,
                "managed_containers": 0,
                "unmanaged_containers": 0,
                "running_containers": 0,
                "stopped_containers": 0,
                "outdated_containers": 0,
            }
