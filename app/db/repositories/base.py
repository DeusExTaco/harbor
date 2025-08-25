# app/db/repositories/base.py
"""
Harbor Base Repository Pattern - FIXED TYPE ANNOTATIONS

Type-safe async repository pattern for database operations with
comprehensive CRUD operations and query building.
"""

from abc import ABC
from typing import Any, Generic, TypeVar

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.db.base import BaseModel
from app.utils.logging import get_logger


logger = get_logger(__name__)

# Generic type for model classes
ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType], ABC):
    """Base repository with common CRUD operations"""

    def __init__(self, session: AsyncSession, model_class: type[ModelType]) -> None:
        self.session = session
        self.model_class = model_class

    async def create(self, **kwargs: Any) -> ModelType:
        """Create a new model instance - doesn't auto-flush"""
        instance = self.model_class(**kwargs)
        self.session.add(instance)

        logger.debug(
            f"Added {self.model_class.__name__} to session (will get ID on flush/commit)"
        )
        return instance

    async def create_and_flush(self, **kwargs: Any) -> ModelType:
        """Create a new model instance and flush immediately (when ID is needed)"""
        instance = self.model_class(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)

        logger.debug(f"Created {self.model_class.__name__} with id {instance.id}")
        return instance

    async def get_by_id(self, id: int) -> ModelType | None:
        """Get model by ID"""
        stmt = select(self.model_class).where(self.model_class.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str | None = None,
    ) -> list[ModelType]:
        """Get all models with optional pagination and ordering"""
        stmt = select(self.model_class)

        # Apply ordering
        if order_by:
            if hasattr(self.model_class, order_by):
                column = getattr(self.model_class, order_by)
                stmt = stmt.order_by(column)

        # Apply pagination
        if limit is not None:
            stmt = stmt.limit(limit)
        if offset is not None:
            stmt = stmt.offset(offset)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_by_id(self, id: int, **kwargs: Any) -> ModelType | None:
        """Update model by ID - doesn't auto-flush"""
        # First check if record exists
        instance = await self.get_by_id(id)
        if not instance:
            return None

        # Update fields
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        # Update timestamp if available
        if hasattr(instance, "update_timestamp"):
            instance.update_timestamp()

        logger.debug(
            f"Updated {self.model_class.__name__} with id {id} (will persist on commit)"
        )
        return instance

    async def delete_by_id(self, id: int) -> bool:
        """Delete model by ID"""
        stmt = delete(self.model_class).where(self.model_class.id == id)
        result = await self.session.execute(stmt)

        deleted = result.rowcount > 0
        if deleted:
            logger.debug(f"Deleted {self.model_class.__name__} with id {id}")

        return deleted

    async def count(self, **filters: Any) -> int:
        """Count models with optional filters"""
        stmt = select(func.count(self.model_class.id))

        # Apply filters
        if filters:
            conditions = []
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    column = getattr(self.model_class, key)
                    conditions.append(column == value)

            if conditions:
                stmt = stmt.where(and_(*conditions))

        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def exists(self, **filters: Any) -> bool:
        """Check if model exists with given filters"""
        count = await self.count(**filters)
        return count > 0

    async def find_by(self, **filters: Any) -> list[ModelType]:
        """Find models by field values"""
        stmt = select(self.model_class)

        # Build WHERE conditions
        conditions = []
        for key, value in filters.items():
            if hasattr(self.model_class, key):
                column = getattr(self.model_class, key)
                if isinstance(value, (list, tuple)):
                    conditions.append(column.in_(value))
                else:
                    conditions.append(column == value)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_one_by(self, **filters: Any) -> ModelType | None:
        """Find single model by field values"""
        results = await self.find_by(**filters)
        return results[0] if results else None

    def _build_query(self) -> Select[tuple[ModelType]]:
        """Build base query - can be overridden by subclasses"""
        return select(self.model_class)


class SearchableRepository(BaseRepository[ModelType]):
    """Repository with search capabilities"""

    async def search(
        self,
        query: str,
        search_fields: list[str],
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[ModelType]:
        """Search models by text query across specified fields"""
        stmt = select(self.model_class)

        # Build search conditions
        if query and search_fields:
            conditions = []
            search_term = f"%{query}%"

            for field in search_fields:
                if hasattr(self.model_class, field):
                    column = getattr(self.model_class, field)
                    conditions.append(column.ilike(search_term))

            if conditions:
                stmt = stmt.where(or_(*conditions))

        # Apply pagination
        if limit is not None:
            stmt = stmt.limit(limit)
        if offset is not None:
            stmt = stmt.offset(offset)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class PaginatedResult(Generic[ModelType]):
    """Paginated query result"""

    def __init__(
        self, items: list[ModelType], total: int, page: int, per_page: int
    ) -> None:
        self.items = items
        self.total = total
        self.page = page
        self.per_page = per_page
        self.pages = (total + per_page - 1) // per_page if per_page > 0 else 1
        self.has_next = page < self.pages
        self.has_prev = page > 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "items": [
                item.to_dict() if hasattr(item, "to_dict") else item
                for item in self.items
            ],
            "pagination": {
                "page": self.page,
                "per_page": self.per_page,
                "total": self.total,
                "pages": self.pages,
                "has_next": self.has_next,
                "has_prev": self.has_prev,
            },
        }


class PaginatedRepository(SearchableRepository[ModelType]):
    """Repository with pagination support"""

    async def paginate(
        self,
        page: int = 1,
        per_page: int = 20,
        order_by: str | None = None,
        **filters: Any,
    ) -> PaginatedResult[ModelType]:
        """Paginate query results"""
        # Validate pagination parameters
        page = max(1, page)
        per_page = min(max(1, per_page), 100)  # Limit to 100 items per page

        # Build base query
        stmt = select(self.model_class)

        # Apply filters
        if filters:
            conditions = []
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    column = getattr(self.model_class, key)
                    if isinstance(value, (list, tuple)):
                        conditions.append(column.in_(value))
                    else:
                        conditions.append(column == value)

            if conditions:
                stmt = stmt.where(and_(*conditions))

        # Count total items - need to handle the WHERE clause properly
        count_stmt = select(func.count(self.model_class.id))
        if filters:
            # Apply the same filters to count query
            if conditions:
                count_stmt = count_stmt.where(and_(*conditions))

        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        # Apply ordering
        if order_by:
            if hasattr(self.model_class, order_by):
                column = getattr(self.model_class, order_by)
                stmt = stmt.order_by(column)

        # Apply pagination
        offset = (page - 1) * per_page
        stmt = stmt.limit(per_page).offset(offset)

        # Execute query
        result = await self.session.execute(stmt)
        items = list(result.scalars().all())

        return PaginatedResult(items=items, total=total, page=page, per_page=per_page)

    async def search_paginated(
        self,
        query: str,
        search_fields: list[str],
        page: int = 1,
        per_page: int = 20,
        **filters: Any,
    ) -> PaginatedResult[ModelType]:
        """Search with pagination"""
        # Validate pagination parameters
        page = max(1, page)
        per_page = min(max(1, per_page), 100)

        # Build base query
        stmt = select(self.model_class)

        # Apply search conditions
        conditions = []
        if query and search_fields:
            search_term = f"%{query}%"
            search_conditions = []

            for field in search_fields:
                if hasattr(self.model_class, field):
                    column = getattr(self.model_class, field)
                    search_conditions.append(column.ilike(search_term))

            if search_conditions:
                conditions.append(or_(*search_conditions))

        # Apply additional filters
        if filters:
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    column = getattr(self.model_class, key)
                    if isinstance(value, (list, tuple)):
                        conditions.append(column.in_(value))
                    else:
                        conditions.append(column == value)

        # Apply all conditions
        if conditions:
            stmt = stmt.where(and_(*conditions))

        # Count total items
        count_stmt = select(func.count(self.model_class.id))
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))

        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * per_page
        stmt = stmt.limit(per_page).offset(offset)

        # Execute query
        result = await self.session.execute(stmt)
        items = list(result.scalars().all())

        return PaginatedResult(items=items, total=total, page=page, per_page=per_page)
