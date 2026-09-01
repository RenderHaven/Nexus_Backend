import json

from app.redis.client import get_redis
from app.redis.keys import RedisKeys

# How long a cached post may be served before it is reloaded from the database.
POST_CACHE_TTL = 8 * 60 * 60


class PostStore:

    def __init__(self):
        self.redis = get_redis()



    def _key(self, post_id: str) -> str:
        return RedisKeys.post(post_id)

    async def set(
        self,
        post_id: str,
        post_data: dict,
    ) -> None:
        await self.redis.set(
            self._key(str(post_id)),
            json.dumps(post_data),
            ex=POST_CACHE_TTL,
        )

    async def get(
        self,
        post_id: str,
    ) -> dict | None:

        data = await self.redis.get(
            self._key(str(post_id))
        )

        if data is None:
            return None

        return json.loads(data)
    
    async def get_many(
        self,
        post_ids: list[str],
    ) -> list[dict | None]:
        if not post_ids:
            return []
            
        keys = [self._key(str(pid)) for pid in post_ids]
        data = await self.redis.mget(keys)
        
        posts = []
        for item in data:
            if item is not None:
                posts.append(json.loads(item))
            else:
                posts.append(None)
                
        return posts

    async def set_many(
        self,
        posts: list[dict],
    ) -> None:
        if not posts:
            return
            
        # mset cannot carry a TTL, so pipeline the individual SETs instead.
        pipeline = self.redis.pipeline()

        for post in posts:
            pipeline.set(
                self._key(str(post["id"])),
                json.dumps(post),
                ex=POST_CACHE_TTL,
            )

        await pipeline.execute()


    async def delete(
        self,
        post_id: str,
    ):

        await self.redis.delete(
            self._key(str(post_id))
        )