import json
from uuid import UUID
from app.redis.client import get_redis
from app.redis.keys import RedisKeys

# How long a cached comment may be served before it is reloaded.
COMMENT_CACHE_TTL = 8 * 60 * 60


class CommentsRedis:
    def __init__(self):
        self.redis = get_redis()

    def _key(self, comment_id: UUID | str) -> str:
        return RedisKeys.comment(str(comment_id))

    async def get_comment(self, comment_id: UUID | str) -> dict | None:
        data = await self.redis.get(self._key(comment_id))
        if data is None:
            return None
        return json.loads(data)

    async def set_comment(self, comment: dict | str, comment_data: dict | None = None) -> None:
        if isinstance(comment, dict):
            cdict = comment
        else:
            cdict = comment_data or {}
            if "id" not in cdict and comment:
                cdict["id"] = comment

        await self.redis.set(
            self._key(str(cdict["id"])),
            json.dumps(cdict),
            ex=COMMENT_CACHE_TTL,
        )

    async def get_many_comments(self, comment_ids: list[UUID | str]) -> list[dict | None]:
        if not comment_ids:
            return []

        keys = [self._key(str(cid)) for cid in comment_ids]
        raw_items = await self.redis.mget(keys)

        results = []
        for item in raw_items:
            if item is not None:
                results.append(json.loads(item))
            else:
                results.append(None)

        return results

    async def set_many_comments(self, comments: list[dict]) -> None:
        if not comments:
            return

        # mset cannot carry a TTL, so pipeline the individual SETs instead.
        pipeline = self.redis.pipeline()

        for comment in comments:
            pipeline.set(
                self._key(str(comment["id"])),
                json.dumps(comment),
                ex=COMMENT_CACHE_TTL,
            )

        await pipeline.execute()

    async def delete_comment(self, comment_id: UUID | str) -> None:
        await self.redis.delete(self._key(comment_id))
