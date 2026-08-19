from app.redis.client import get_redis
from app.redis.keys import RedisKeys
import json

class CategoryStore:
    def __init__(self):
        self.redis=get_redis()
        self.keys=RedisKeys()

    def _key(self, category_id: str = 'all') -> str:
        return self.keys.category(category_id)

    async def set_all_categories(self,categories:dict):
        await self.redis.set(
                    self._key(),
                    json.dumps(categories)
                )
    
    async def get_all_categories(self):
        categories=await self.redis.get(self._key())
        if categories is None:
            return None
        return json.loads(categories)
    
    async def set_category(self,category_id:str,category:dict):
        await self.redis.set(self._key(category_id),json.dumps(category))
    
    async def get_category(self,category_id:str):
        category=await self.redis.get(self._key(category_id))
        if category is None:
            return None
        return json.loads(category)
    
    async def delete_category(self,category_id:str):
        await self.redis.delete(self._key(category_id))

    async def delete_all_categories(self):
        await self.redis.delete(self._key())
    