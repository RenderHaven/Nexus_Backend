from app.redis.client import get_redis
from app.redis.keys import RedisKeys
import json

class CategoryStore:
    def __init__(self):
        self.redis=get_redis()
        self.keys=RedisKeys()

    async def set_all_categories(self,categories:dict):
        await self.redis.set(
                    RedisKeys.category(),
                    json.dumps(categories)
                )
    
    async def get_all_categories(self):
        categories=await self.redis.get(RedisKeys.category())
        if categories is None:
            return None
        return json.loads(categories)
    
    async def set_category(self,category_id:str,category:dict):
        await self.redis.set(RedisKeys.category(category_id),json.dumps(category))
    
    async def get_category(self,category_id:str):
        category=await self.redis.get(RedisKeys.category(category_id))
        if category is None:
            return None
        return json.loads(category)
    
    async def delete_category(self,category_id:str):
        await self.redis.delete(RedisKeys.category(category_id))

    async def delete_all_categories(self):
        await self.redis.delete(RedisKeys.category())
    