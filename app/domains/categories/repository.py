from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Category
from .domain import CategoryBasic

class CategoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_category(self, category_id: UUID) -> CategoryBasic | None:
        result = await self.db.execute(select(Category).where(Category.id == category_id))
        category = result.scalars().first()
        if not category:
            return None
        return CategoryBasic.model_validate(category)

    async def get_all_categories(self) -> list[CategoryBasic]:
        result = await self.db.execute(select(Category))
        categories = result.scalars().all()
        return [CategoryBasic.model_validate(c) for c in categories]
