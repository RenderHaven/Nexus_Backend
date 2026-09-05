from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from .schemas import CategoryBasic
from .repository import CategoryRepository
from .redis import CategoryRedisStore
from app.redis import metrics

class CategoryStorage:
    def __init__(self, db: AsyncSession):
        self.repository = CategoryRepository(db)
        self.redis_store = CategoryRedisStore()

    async def get_categories_by_id(
        self,
        category_ids: list[UUID],
    ) -> dict[UUID, CategoryBasic]:
        """
        Resolve a batch of category ids for hydrating a list.

        Deliberately not served off category:all -- that key answers
        "give me every category", which is a different question from
        "resolve these four ids".
        """
        if not category_ids:
            return {}

        unique_ids = list(dict.fromkeys(category_ids))
        cached = await self.redis_store.get_many(unique_ids)

        result: dict[UUID, CategoryBasic] = {}
        missing: list[UUID] = []

        for category_id, category in zip(unique_ids, cached):
            if category:
                result[category_id] = category
            else:
                missing.append(category_id)

        await metrics.record("category", hits=len(result), misses=len(missing))

        if missing:
            rows = await self.repository.categories_by_ids(missing)
            for category in rows:
                result[category.id] = category
            await self.redis_store.set_many(rows)

        return result

    async def get_category(self, category_id: UUID) -> CategoryBasic | None:
        category = await self.redis_store.get_category(category_id)
        if category:
            await metrics.record("category", hits=1)
            return category

        await metrics.record("category", misses=1)

        category = await self.repository.get_category(category_id)
        if category:
            await self.redis_store.set_category(category)
        return category

    async def get_all_categories(self) -> list[CategoryBasic]:
        categories = await self.redis_store.get_all_categories()
        if categories:
            await metrics.record("category_all", hits=1)
            return categories

        await metrics.record("category_all", misses=1)

        categories = await self.repository.get_all_categories()
        if categories:
            await self.redis_store.set_all_categories(categories)
            for cat in categories:
                await self.redis_store.set_category(cat)
        return categories
