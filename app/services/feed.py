import random as rand
from collections import defaultdict
from email.policy import default
from uuid import UUID
from app.storage.categories import CategoryStorage
from app.domains.feed.pools.popular import PopularPool
from app.storage.pool import PoolStorage
from app.services.post import PostService

class FeedService:

    def __init__(self, db):
        self.feed_size=100
        self.post_svc=PostService(db)
        self.pool_storage=PoolStorage(db)
        self.category_store=CategoryStorage(db)
        self.pools = {
            "popular": PopularPool(pool_probablity=10),
        }

    async def build_pools(self):
        for pool in self.pools.values():
            await self.pool_storage.build(pool)
    
    async def get_category_probablities(self,user_id:UUID|None =None):
        categories= await self.category_store.get_all()
        categories_probablity = {}
        for category in categories:
            categories_probablity[str(category.id)] = (10,round(rand.random(),2))
        return categories_probablity
    
    async def get_pool_posts(self,pool_name:str,categories_probablities:dict[str,(int,float)],limit:int=100):
        post_ids=await self.pool_storage.get_posts_ids_by_categories(
            pool_name,
            limit,
            categories_probablities
        )

        posts=defaultdict(list)
        for category_id,post_ids in post_ids.items():
            posts[category_id]=await self.post_svc.get_posts(post_ids)
        return posts
    
    async def get_posts_with_pools(self,user_id:UUID|None =None,offset=0):
        """Get posts with pools."""
        feed_post_ids=dict()
        category_probablities = await self.get_category_probablities(user_id)
        buffer=0
        for pool in self.pools.values():
            actual_limit=int(self.feed_size * pool.pool_probablity / 100)
            extra_limit = buffer*pool.pool_probablity/100
            limit = int(actual_limit + extra_limit)
            posts=await self.get_pool_posts(pool,category_probablities,limit)
            feed_post_ids[pool.pool_name]=posts
            if len(posts)<limit:
                buffer+=(limit-len(posts))
        
        return feed_post_ids