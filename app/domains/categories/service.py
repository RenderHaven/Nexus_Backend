from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from .storage import CategoryStorage
from .schemas import CategoryBasic

class CategoryService:
    def __init__(self, db: AsyncSession):
        self.storage = CategoryStorage(db)

    async def get_category(self, category_id: UUID) -> CategoryBasic | None:
        return await self.storage.get_category(category_id)

    async def get_categories_by_id(
        self,
        category_ids: list[UUID],
    ) -> dict[UUID, CategoryBasic]:
        """Batch id -> category, for hydrating a list of posts."""
        return await self.storage.get_categories_by_id(category_ids)

    async def get_all_categories(self) -> list[CategoryBasic]:
        return await self.storage.get_all_categories()
