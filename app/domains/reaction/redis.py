from uuid import UUID
from app.redis.client import get_redis
from app.redis.keys import RedisKeys

class ReactionRedis:
    def __init__(self):
        self.redis = get_redis()

    def _key(self, user_id: UUID | str) -> str:
        return RedisKeys.user_liked_posts(str(user_id))

    async def is_exist(self,user_id:UUID|str)->bool:
        return await self.redis.exists(self.redis_store._key(user_id))

    async def update(self, post_id: UUID | str, user_id: UUID | str, like: bool):
        key = self._key(user_id)
        if like:
            await self.redis.sadd(key, str(post_id))
        else:
            await self.redis.srem(key, str(post_id))

    async def are_liked(self, post_ids: list[str], user_id: str) -> dict[str, bool]:
        if not post_ids:
            return {}
        results = await self.redis.smismember(self._key(user_id), post_ids)
        return dict(zip(post_ids, map(bool, results)))
