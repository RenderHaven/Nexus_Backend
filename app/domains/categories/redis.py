import json
from uuid import UUID
from app.redis.client import get_redis
from app.redis.keys import RedisKeys
from .schemas import CategoryBasic

class CategoryRedisStore:
    def __init__(self):
        self.redis = get_redis()

    def _key(self, category_id: UUID | str) -> str:
        return f"category:{str(category_id)}"

    def _all_key(self) -> str:
        return "category:all"

    async def set_category(self, category: CategoryBasic) -> None:
        await self.redis.set(self._key(category.id), category.model_dump_json())

    async def get_category(self, category_id: UUID) -> CategoryBasic | None:
        data = await self.redis.get(self._key(category_id))
        if not data:
            return None
        return CategoryBasic.model_validate_json(data)

    async def get_many(self, category_ids: list[UUID]) -> list[CategoryBasic | None]:
        """One MGET over category:{id}. Positional -- a miss comes back as None."""
        if not category_ids:
            return []

        data = await self.redis.mget([self._key(cid) for cid in category_ids])
        return [
            CategoryBasic.model_validate_json(item) if item is not None else None
            for item in data
        ]

    async def set_many(self, categories: list[CategoryBasic]) -> None:
        if not categories:
            return

        pipeline = self.redis.pipeline()

        for category in categories:
            pipeline.set(self._key(category.id), category.model_dump_json())

        await pipeline.execute()

    async def set_all_categories(self, categories: list[CategoryBasic]) -> None:
        data = [c.model_dump(mode="json") for c in categories]
        await self.redis.set(self._all_key(), json.dumps(data))

    async def get_all_categories(self) -> list[CategoryBasic] | None:
        data = await self.redis.get(self._all_key())
        if not data:
            return None
        return [CategoryBasic(**c) for c in json.loads(data)]
