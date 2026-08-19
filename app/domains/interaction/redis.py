from uuid import UUID
from app.redis.client import get_redis
from app.redis.keys import RedisKeys

class InteractionRedis:
    def __init__(self):
        self.redis = get_redis()

    def _key(self, post_id: UUID | str) -> str:
        return RedisKeys.post_likes(str(post_id))

    async def update(self, post_id: UUID | str, user_id: UUID | str, like: bool):
        key = self._key(post_id)
        if like:
            await self.redis.sadd(key, str(user_id))
        else:
            await self.redis.srem(key, str(user_id))

    async def get_count(self, post_id: UUID | str) -> int:
        return await self.redis.scard(self._key(post_id))

    async def is_liked(self, post_id: UUID | str, user_id: UUID | str) -> bool:
        return await self.redis.sismember(self._key(post_id), str(user_id))
