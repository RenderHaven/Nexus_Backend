from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from .schemas import CategoryBasic
from .repository import CategoryRepository
from .redis import CategoryRedisStore

class CategoryStorage:
    def __init__(self, db: AsyncSession):
        self.repository = CategoryRepository(db)
        self.redis_store = CategoryRedisStore()

    async def get_category(self, category_id: UUID) -> CategoryBasic | None:
        category = await self.redis_store.get_category(category_id)
        if category:
            return category
        
        category = await self.repository.get_category(category_id)
        if category:
            await self.redis_store.set_category(category)
        return category

    async def get_all_categories(self) -> list[CategoryBasic]:
        categories = await self.redis_store.get_all_categories()
        if categories:
            return categories
        
        categories = await self.repository.get_all_categories()
        if categories:
            await self.redis_store.set_all_categories(categories)
            for cat in categories:
                await self.redis_store.set_category(cat)
        return categories
