import json

from app.redis.client import get_redis
from app.redis.keys import RedisKeys


class PostStore:

    def __init__(self):
        self.redis = get_redis()

    def active_posts_key(self) -> str:
        return RedisKeys.active_posts()

    async def add_active_post(self, post_id: str):
        await self.redis.sadd(self.active_posts_key(), post_id)

    async def remove_active_post(self, post_id: str):
        await self.redis.srem(self.active_posts_key(), post_id)

    async def rebuild_registry(self, post_ids: list[str]):
        key = self.active_posts_key()
        temp_key = f"{key}:tmp"
        pipeline = self.redis.pipeline()
        if post_ids:
            pipeline.sadd(temp_key, *post_ids)
        pipeline.rename(temp_key, key)
        await pipeline.execute()

    def _key(self, post_id: str) -> str:
        return RedisKeys.post(post_id)

    async def set(
        self,
        post: dict | str,
        post_data: dict | None = None,
    ) -> None:
        if isinstance(post, dict):
            pdict = post
        else:
            pdict = post_data or {}
            if "id" not in pdict and post:
                pdict["id"] = post

        await self.redis.set(
            self._key(str(pdict["id"])),
            json.dumps(pdict),
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
    ) -> list[dict]:
        if not post_ids:
            return []
            
        # 1. Convert all strs into their corresponding Redis keys
        keys = [self._key(str(pid)) for pid in post_ids]
        
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
        posts: list[dict],
    ) -> None:
        if not posts:
            return
            
        # 1. Create a dictionary mapping of "Redis Key" -> "JSON String"
        mapping = {
            self._key(str(post["id"])): json.dumps(post)
            for post in posts
        }
        
        # 2. Set all keys at once using mset
        await self.redis.mset(mapping)


    async def delete(
        self,
        post_id: str,
    ):

        await self.redis.delete(
            self._key(str(post_id))
        )