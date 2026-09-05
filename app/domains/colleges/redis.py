import json
from uuid import UUID
from app.redis.client import get_redis
from app.redis.keys import RedisKeys
from .schemas import CollegeBasic

# How long a cached college may be served before it is reloaded.
COLLEGE_CACHE_TTL = 8 * 60 * 60

class CollegeRedisStore:
    def __init__(self):
        self.redis = get_redis()

    def _key(self, college_id: UUID | str) -> str:
        return f"college:{str(college_id)}"

    async def set_college(self, college: CollegeBasic) -> None:
        await self.redis.set(
            self._key(college.id),
            college.model_dump_json(),
            ex=COLLEGE_CACHE_TTL,
        )

    async def get_many(self, college_ids: list[UUID]) -> list[CollegeBasic | None]:
        """One MGET over college:{id}. Positional -- a miss comes back as None."""
        if not college_ids:
            return []

        data = await self.redis.mget([self._key(cid) for cid in college_ids])
        return [
            CollegeBasic.model_validate_json(item) if item is not None else None
            for item in data
        ]

    async def set_many(self, colleges: list[CollegeBasic]) -> None:
        """MSET cannot carry a TTL, so the individual SETs are pipelined."""
        if not colleges:
            return

        pipeline = self.redis.pipeline()

        for college in colleges:
            pipeline.set(
                self._key(college.id),
                college.model_dump_json(),
                ex=COLLEGE_CACHE_TTL,
            )

        await pipeline.execute()

    async def delete_college(self, college_id: UUID | str) -> None:
        await self.redis.delete(self._key(college_id))

    async def get_college(self, college_id: UUID) -> CollegeBasic | None:
        data = await self.redis.get(self._key(college_id))
        if not data:
            return None
        return CollegeBasic.model_validate_json(data)
