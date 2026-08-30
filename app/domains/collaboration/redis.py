from uuid import UUID
from app.redis.client import get_redis
from app.redis.keys import RedisKeys

class CollaborationRedis:
    def __init__(self):
        self.redis = get_redis()

    def _key(self, user_id: UUID | str) -> str:
        return RedisKeys.user_collab_status(str(user_id))

    async def is_exist(self, user_id: UUID | str) -> bool:
        return await self.redis.exists(self._key(user_id))

    async def set_status(self, user_id: UUID | str, post_id: UUID | str, status: str):
        key = self._key(user_id)
        await self.redis.hset(key, str(post_id), status)

    async def get_statuses(self, post_ids: list[str], user_id: str) -> dict[str, str]:
        if not post_ids:
            return {}
        key = self._key(user_id)
        values = await self.redis.hmget(key, post_ids)
        return {pid: status for pid, status in zip(post_ids, values) if status is not None}
