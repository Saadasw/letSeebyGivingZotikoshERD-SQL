"""Branch service."""

from typing import Any, Optional, Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.db.models.branch import Branch
from app.repositories.branch import BranchRepository


class BranchService:
    """Branch management service."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.branch_repo = BranchRepository(db)

    async def get_branch(self, branch_id: UUID) -> Optional[Branch]:
        """Get branch by ID."""
        return await self.branch_repo.get(branch_id)

    async def get_branch_by_code(self, code: str) -> Optional[Branch]:
        """Get branch by code."""
        return await self.branch_repo.get_by_code(code)

    async def get_main_branch(self) -> Optional[Branch]:
        """Get the main branch."""
        return await self.branch_repo.get_main_branch()

    async def get_branches(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Sequence[Branch]:
        """Get list of branches with filters."""
        return await self.branch_repo.get_branches_list(
            skip=skip,
            limit=limit,
            search=search,
            city=city,
            state=state,
            is_active=is_active,
        )

    async def count_branches(
        self,
        *,
        city: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> int:
        """Count branches matching filters."""
        return await self.branch_repo.count_branches(
            city=city,
            is_active=is_active,
        )

    async def create_branch(
        self,
        name: str,
        code: str,
        **branch_data,
    ) -> Branch:
        """Create a new branch."""
        # Check if code exists
        existing = await self.branch_repo.get_by_code(code)
        if existing:
            raise ConflictError("Branch code already exists")

        # Check if this should be main branch
        is_main = branch_data.get("is_main", False)
        if is_main:
            main = await self.branch_repo.get_main_branch()
            if main:
                raise ConflictError("A main branch already exists")

        branch = await self.branch_repo.create({
            "name": name,
            "code": code,
            **branch_data,
        })

        await self.db.commit()
        await self.db.refresh(branch)

        return branch

    async def update_branch(
        self,
        branch_id: UUID,
        **update_data,
    ) -> Optional[Branch]:
        """Update branch."""
        branch = await self.branch_repo.get(branch_id)
        if not branch:
            raise NotFoundError("Branch not found")

        # Check code uniqueness if updating
        if "code" in update_data and update_data["code"] != branch.code:
            existing = await self.branch_repo.get_by_code(update_data["code"])
            if existing:
                raise ConflictError("Branch code already in use")

        # Check main branch constraint
        if update_data.get("is_main", False) and not branch.is_main:
            main = await self.branch_repo.get_main_branch()
            if main:
                raise ConflictError("A main branch already exists")

        updated = await self.branch_repo.update(branch_id, update_data)
        await self.db.commit()

        return updated

    async def delete_branch(self, branch_id: UUID) -> bool:
        """Delete branch (soft delete by deactivating)."""
        branch = await self.branch_repo.get(branch_id)
        if not branch:
            raise NotFoundError("Branch not found")

        if branch.is_main:
            raise ConflictError("Cannot delete the main branch")

        await self.branch_repo.update(branch_id, {"is_active": False})
        await self.db.commit()

        return True

    async def activate_branch(self, branch_id: UUID) -> Optional[Branch]:
        """Activate branch."""
        return await self.update_branch(branch_id, is_active=True)

    async def deactivate_branch(self, branch_id: UUID) -> Optional[Branch]:
        """Deactivate branch."""
        branch = await self.branch_repo.get(branch_id)
        if not branch:
            raise NotFoundError("Branch not found")

        if branch.is_main:
            raise ConflictError("Cannot deactivate the main branch")

        return await self.update_branch(branch_id, is_active=False)

    async def get_branch_with_stats(self, branch_id: UUID) -> Optional[dict[str, Any]]:
        """Get branch with statistics."""
        return await self.branch_repo.get_branch_with_stats(branch_id)

    async def get_branch_stats(self) -> dict[str, Any]:
        """Get overall branch statistics."""
        return await self.branch_repo.get_branch_stats()
