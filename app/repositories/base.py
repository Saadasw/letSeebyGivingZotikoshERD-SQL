"""Base repository with common CRUD operations."""

from typing import Any, Generic, Optional, Sequence, Type, TypeVar
from uuid import UUID

from sqlalchemy import and_, func, or_, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import Base


ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations."""

    def __init__(self, model: Type[ModelType], db: AsyncSession):
        """Initialize repository with model class and database session."""
        self.model = model
        self.db = db

    async def get(
        self,
        id: UUID,
        options: Optional[list] = None,
    ) -> Optional[ModelType]:
        """Get a single record by ID."""
        query = select(self.model).where(self.model.id == id)
        if options:
            for opt in options:
                query = query.options(opt)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_field(
        self,
        field: str,
        value: Any,
        options: Optional[list] = None,
    ) -> Optional[ModelType]:
        """Get a single record by a specific field."""
        query = select(self.model).where(getattr(self.model, field) == value)
        if options:
            for opt in options:
                query = query.options(opt)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False,
        options: Optional[list] = None,
    ) -> Sequence[ModelType]:
        """Get multiple records with pagination and filtering."""
        query = select(self.model)

        # Apply filters
        if filters:
            conditions = []
            for field, value in filters.items():
                if value is not None:
                    if isinstance(value, list):
                        conditions.append(getattr(self.model, field).in_(value))
                    else:
                        conditions.append(getattr(self.model, field) == value)
            if conditions:
                query = query.where(and_(*conditions))

        # Apply eager loading options
        if options:
            for opt in options:
                query = query.options(opt)

        # Apply ordering
        if order_by and hasattr(self.model, order_by):
            order_column = getattr(self.model, order_by)
            query = query.order_by(order_column.desc() if order_desc else order_column)
        elif hasattr(self.model, "created_at"):
            query = query.order_by(self.model.created_at.desc())

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_all(
        self,
        filters: Optional[dict[str, Any]] = None,
        options: Optional[list] = None,
    ) -> Sequence[ModelType]:
        """Get all records matching filters."""
        query = select(self.model)

        if filters:
            conditions = []
            for field, value in filters.items():
                if value is not None:
                    conditions.append(getattr(self.model, field) == value)
            if conditions:
                query = query.where(and_(*conditions))

        if options:
            for opt in options:
                query = query.options(opt)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def count(
        self,
        filters: Optional[dict[str, Any]] = None,
    ) -> int:
        """Count records matching filters."""
        query = select(func.count(self.model.id))

        if filters:
            conditions = []
            for field, value in filters.items():
                if value is not None:
                    conditions.append(getattr(self.model, field) == value)
            if conditions:
                query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def exists(
        self,
        filters: dict[str, Any],
    ) -> bool:
        """Check if a record exists matching filters."""
        query = select(func.count(self.model.id)).where(
            and_(*[getattr(self.model, k) == v for k, v in filters.items() if v is not None])
        )
        result = await self.db.execute(query)
        return (result.scalar() or 0) > 0

    async def create(
        self,
        obj_in: dict[str, Any],
    ) -> ModelType:
        """Create a new record."""
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def create_many(
        self,
        objs_in: list[dict[str, Any]],
    ) -> list[ModelType]:
        """Create multiple records."""
        db_objs = [self.model(**obj) for obj in objs_in]
        self.db.add_all(db_objs)
        await self.db.flush()
        for obj in db_objs:
            await self.db.refresh(obj)
        return db_objs

    async def update(
        self,
        id: UUID,
        obj_in: dict[str, Any],
    ) -> Optional[ModelType]:
        """Update a record by ID."""
        db_obj = await self.get(id)
        if not db_obj:
            return None

        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def update_by_filter(
        self,
        filters: dict[str, Any],
        obj_in: dict[str, Any],
    ) -> int:
        """Update records matching filters."""
        conditions = [
            getattr(self.model, k) == v for k, v in filters.items() if v is not None
        ]
        query = update(self.model).where(and_(*conditions)).values(**obj_in)
        result = await self.db.execute(query)
        await self.db.flush()
        return result.rowcount

    async def delete(
        self,
        id: UUID,
    ) -> bool:
        """Delete a record by ID."""
        db_obj = await self.get(id)
        if not db_obj:
            return False

        await self.db.delete(db_obj)
        await self.db.flush()
        return True

    async def delete_by_filter(
        self,
        filters: dict[str, Any],
    ) -> int:
        """Delete records matching filters."""
        conditions = [
            getattr(self.model, k) == v for k, v in filters.items() if v is not None
        ]
        query = delete(self.model).where(and_(*conditions))
        result = await self.db.execute(query)
        await self.db.flush()
        return result.rowcount

    async def soft_delete(
        self,
        id: UUID,
    ) -> Optional[ModelType]:
        """Soft delete a record by setting is_deleted=True."""
        if not hasattr(self.model, "is_deleted"):
            raise AttributeError(f"{self.model.__name__} does not support soft delete")

        return await self.update(id, {"is_deleted": True})

    async def search(
        self,
        search_fields: list[str],
        search_term: str,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[dict[str, Any]] = None,
    ) -> Sequence[ModelType]:
        """Search records by multiple fields."""
        query = select(self.model)

        # Build search conditions
        search_conditions = []
        for field in search_fields:
            if hasattr(self.model, field):
                search_conditions.append(
                    getattr(self.model, field).ilike(f"%{search_term}%")
                )

        if search_conditions:
            query = query.where(or_(*search_conditions))

        # Apply additional filters
        if filters:
            conditions = []
            for field, value in filters.items():
                if value is not None:
                    conditions.append(getattr(self.model, field) == value)
            if conditions:
                query = query.where(and_(*conditions))

        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()


class SoftDeleteRepository(BaseRepository[ModelType]):
    """Repository for models with soft delete support."""

    async def get(
        self,
        id: UUID,
        options: Optional[list] = None,
        include_deleted: bool = False,
    ) -> Optional[ModelType]:
        """Get a single record by ID, excluding soft-deleted by default."""
        query = select(self.model).where(self.model.id == id)

        if not include_deleted and hasattr(self.model, "is_deleted"):
            query = query.where(self.model.is_deleted == False)

        if options:
            for opt in options:
                query = query.options(opt)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False,
        options: Optional[list] = None,
        include_deleted: bool = False,
    ) -> Sequence[ModelType]:
        """Get multiple records, excluding soft-deleted by default."""
        filters = filters or {}
        if not include_deleted and hasattr(self.model, "is_deleted"):
            filters["is_deleted"] = False

        return await super().get_multi(
            skip=skip,
            limit=limit,
            filters=filters,
            order_by=order_by,
            order_desc=order_desc,
            options=options,
        )

    async def restore(
        self,
        id: UUID,
    ) -> Optional[ModelType]:
        """Restore a soft-deleted record."""
        if not hasattr(self.model, "is_deleted"):
            raise AttributeError(f"{self.model.__name__} does not support soft delete")

        db_obj = await self.get(id, include_deleted=True)
        if not db_obj:
            return None

        db_obj.is_deleted = False
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj
