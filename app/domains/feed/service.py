
from app.domains.categories.service import CategoryService
from app.domains.feed.pools.base import BasePool
import random as rand
from collections import defaultdict
from uuid import UUID
from app.domains.feed.pools.popular import PopularPool
from app.domains.feed.pools.pool import PoolStorage
from app.domains.post.service import PostService
from app.domains.user.service import UserService

class FeedService:

    def __init__(self, db):
        self.feed_size=100
        self.post_svc=PostService(db)
        self.user_svc=UserService(db)
        self.category_svc=CategoryService(db)
        self.pool_storage=PoolStorage(db)
        self.pools = {
            "popular": PopularPool(pool_probablity=10),
        }

    async def build_pools(self):
        for pool in self.pools.values():
            await self.pool_storage.build(pool)
    
    async def get_pool_post_ids(self,pool:BasePool,categories_probablities:dict[str,(int,float)],limit:int=100):
        post_ids = {}
        for category_id, (offset,probablity) in categories_probablities.items():
            post_ids[category_id]= await self.pool_storage.get_post_ids_for_category(
                pool,category_id,offset,int(limit*probablity)
            )
        return post_ids
    
    async def get_dummy_category_probabilities(self):
        categories=await self.category_svc.get_all_categories()
        cat_prob_dict={}
        for category in categories:
            cat_prob_dict[str(category.id)]=(0,1/len(categories))
        return cat_prob_dict
    
    async def get_category_probabilities(self,user_id:UUID):
        prefrence=await self.user_svc.get_category_preferences(user_id)

        if not prefrence:
            return await self.get_dummy_category_probabilities()
        
        cat_prob_dict={}
        total_weight=sum(category.weight for category in prefrence)
        for category in prefrence:
            cat_prob_dict[str(category.category_id)]=(0,category.weight/total_weight)
            
        return cat_prob_dict

    async def get_post_ids(self,user_id:UUID|None =None,offset=0):
        """Get posts with pools."""
        feed_post_ids=dict()
        category_probablities = await self.get_category_probabilities(user_id)
        buffer=0
        for pool in self.pools.values():
            actual_limit=int(self.feed_size * pool.pool_probablity / 100)
            extra_limit = buffer*pool.pool_probablity/100
            limit = int(actual_limit + extra_limit)
            posts_ids=await self.get_pool_post_ids(pool,category_probablities,limit)
            feed_post_ids[pool.pool_name]=posts_ids
            if len(posts_ids)<limit:
                buffer+=(limit-len(posts_ids))
        
        return feed_post_ids
    
    async def get_posts(self,user_id:UUID|None =None,offset=0):
        post_ids=await self.get_post_ids(user_id,offset)
        feed_posts=defaultdict()
        for pool_name,ids in post_ids.items():
            feed_posts[pool_name]=await self.post_svc.get_posts(ids)
        
        return feed_posts