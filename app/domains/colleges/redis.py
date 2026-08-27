import json
from uuid import UUID
from app.redis.client import get_redis
from app.redis.keys import RedisKeys
from .schemas import CollegeBasic

class CollegeRedisStore:
    def __init__(self):
        self.redis = get_redis()

    def _key(self, college_id: UUID | str) -> str:
        return f"college:{str(college_id)}"

    async def set_college(self, college: CollegeBasic) -> None:
        await self.redis.set(self._key(college.id), college.model_dump_json())

    async def get_college(self, college_id: UUID) -> CollegeBasic | None:
        data = await self.redis.get(self._key(college_id))
        if not data:
            return None
        return CollegeBasic.model_validate_json(data)
