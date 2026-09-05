from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Category
from .schemas import CategoryBasic

class CategoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_category(self, category_id: UUID) -> CategoryBasic | None:
        result = await self.db.execute(select(Category).where(Category.id == category_id))
        category = result.scalars().first()
        if not category:
            return None
        return CategoryBasic.model_validate(category)

    async def categories_by_ids(self, category_ids: list[UUID]) -> list[CategoryBasic]:
        """Full rows for a set of ids -- see CollegeRepository.colleges_by_ids."""
        if not category_ids:
            return []

        result = await self.db.execute(
            select(Category).where(Category.id.in_(category_ids))
        )
        return [CategoryBasic.model_validate(c) for c in result.scalars().all()]

    async def get_all_categories(self) -> list[CategoryBasic]:
        result = await self.db.execute(select(Category))
        categories = result.scalars().all()
        return [CategoryBasic.model_validate(c) for c in categories]
