import json
from uuid import UUID

from app.redis.client import get_redis
from app.redis.keys import RedisKeys


class UserRedisStore:
    def __init__(self):
        self.redis = get_redis()

    def _key(self, user_id: UUID | str) -> str:
        return RedisKeys.user(str(user_id))

    def _profile_key(self, user_id: UUID | str) -> str:
        return RedisKeys.user_profile(str(user_id))

    async def set(self, user_id: UUID | str, user: dict) -> None:
        await self.redis.set(self._key(user_id), json.dumps(user))

    async def get(self, user_id: UUID | str) -> dict | None:
        data = await self.redis.get(self._key(user_id))
        if data is None:
            return None
        return json.loads(data)

    async def delete(self, user_id: UUID | str) -> None:
        await self.redis.delete(self._key(user_id), self._profile_key(user_id))

    async def set_profile(self, user_id: UUID | str, profile: dict) -> None:
        await self.redis.set(self._profile_key(user_id), json.dumps(profile))

    async def get_profile(self, user_id: UUID | str) -> dict | None:
        data = await self.redis.get(self._profile_key(user_id))
        if data is None:
            return None
        return json.loads(data)
