import json
from uuid import UUID

from app.redis.client import get_redis
from app.redis.keys import RedisKeys


class PostStore:

    def __init__(self):
        self.redis = get_redis()

    async def set(
        self,
        post_id: UUID,
        post: dict,
    ) -> None:

        await self.redis.set(
            RedisKeys.post(str(post_id)),
            json.dumps(post),
        )

    async def get(
        self,
        post_id: UUID,
    ) -> dict | None:

        data = await self.redis.get(
            RedisKeys.post(str(post_id))
        )

        if data is None:
            return None

        return json.loads(data)
    
    async def get_many(
        self,
        post_ids: list[UUID],
    ) -> list[dict]:
        if not post_ids:
            return []
            
        # 1. Convert all UUIDs into their corresponding Redis keys
        keys = [RedisKeys.post(str(pid)) for pid in post_ids]
        
        # 2. Fetch all keys at once using mget
        data = await self.redis.mget(keys)
        
        # 3. Parse only the ones that were found in Redis
        posts = []
        for item in data:
            if item is not None:
                posts.append(json.loads(item))
                
        return posts

    async def set_many(
        self,
        post_ids: list[UUID],
        posts: list[dict],
    ) -> None:
        if not posts:
            return
            
        # 1. Create a dictionary mapping of "Redis Key" -> "JSON String"
        mapping = {
            RedisKeys.post(str(post["id"])): json.dumps(post)
            for post in posts
        }
        
        # 2. Set all keys at once using mset
        await self.redis.mset(mapping)


    async def delete(
        self,
        post_id: UUID,
    ):

        await self.redis.delete(
            RedisKeys.post(str(post_id))
        )