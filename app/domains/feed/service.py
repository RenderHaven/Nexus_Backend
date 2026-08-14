
import random as random
from app.domains.feed.utils import get_snapshot_key
from app.domains.feed.feed_snapshot.service import FeedSnapshotService
from app.domains.feed.feed_snapshot.domain import FeedSnapshot
from app.domains.categories.service import CategoryService
from app.domains.feed.pool.core.pools.base import BasePool
from collections import defaultdict
from uuid import UUID
from app.domains.feed.pool.core.pools.popular import PopularPool
from app.domains.feed.pool.storage import PoolStorage
from app.domains.post.service import PostService
from app.domains.user.service import UserService

class FeedService:

    def __init__(self, db):
        self.feed_size=100
        self.post_svc=PostService(db)
        self.user_svc=UserService(db)
        self.feed_snapshot_svc=FeedSnapshotService()
        self.category_svc=CategoryService(db)
        self.pool_storage=PoolStorage(db)
        self.pools = {
            "popular": PopularPool(pool_probablity=50),
        }
    
    async def _feed_snapshot(self,feed_id:UUID|None=None):
        snapshot=await self.feed_snapshot_svc.get_snapshot(feed_id)
        return snapshot

    async def get_feed_snapshot(self,feed_id:UUID|None=None):
        return await self._feed_snapshot(feed_id)

    async def build_pools(self):
        for pool in self.pools.values():
            await self.pool_storage.build(pool)
    
    async def _get_offsets(self,feed_snapshot:FeedSnapshot|None,pool_name:str,category_id:str|None=None):
        if feed_snapshot and feed_snapshot.offsets is not None:
            key=get_snapshot_key(pool_name,category_id)
            return feed_snapshot.offsets.get(key,0)
        return 0
                
    
    async def _get_categories_probablity(self,pool_name:str,feed_snapshot:FeedSnapshot|None,preferences:dict[str,float])->dict[str,(int,float)]:
        categories_probablity={}
        for category_id, probablity in preferences.items():
            offset=await self._get_offsets(feed_snapshot,pool_name,category_id)
            categories_probablity[category_id]=(offset,probablity)
        return categories_probablity

    async def _get_pool_post_ids(self,pool:BasePool,categories_probablity:dict[str,(int,float)],limit:int=100)->dict[str,list[UUID]]:
        post_ids,new_offsets = await self.pool_storage.get_posts_ids_by_categories(pool,limit,categories_probablity)
        offsets=defaultdict()
        for category_id,offset in new_offsets.items():
            key=get_snapshot_key(pool.pool_name,category_id)
            offsets[key]=offset
        return post_ids,offsets
    
    async def _get_dummy_preferences(self)->dict[str,float]:
        categories=await self.category_svc.get_all_categories()
        
        preferences={}      # 1/n for all categories
        for category in categories:
            preferences[str(category.id)] = random.random()
        return preferences
    
    async def get_preferences(self,user_id:UUID|None=None)->dict[str,float]:
        preferences=await self.user_svc.get_category_preferences(user_id)

        if not preferences:
            return await self._get_dummy_preferences()
        
        return preferences

    async def get_post_ids(self,user_id:UUID|None =None,feed_id:UUID|None=None):
        """Get posts with pools."""
        feed_post_ids=dict()

        ##Prefrence and feed snapshot
        preferences = await self.get_preferences(user_id)

        feed_snapshot=await self._feed_snapshot(feed_id)

        # need to apply snapshot for user here
        new_offsets={}
        buffer=0
        for pool in self.pools.values():
            actual_limit=int(self.feed_size * pool.pool_probablity / 100)
            extra_limit = buffer*pool.pool_probablity/100
            limit = int(actual_limit + extra_limit)
            categories_probablity=await self._get_categories_probablity(pool.pool_name,feed_snapshot,preferences)
            posts_ids,updated_offsets=await self._get_pool_post_ids(pool,categories_probablity,limit)
            feed_post_ids[pool.pool_name]=posts_ids
            new_offsets.update(updated_offsets)
            
            if len(posts_ids)<limit:
                buffer+=(limit-len(posts_ids))
        
        ##Update feed_snapshot here
        new_feed_id=await self.feed_snapshot_svc.update_snapshot(user_id,new_offsets,feed_id)

        return feed_post_ids,new_feed_id
    
    async def get_posts(self,user_id:UUID|None =None,feed_id:UUID|None=None):
        post_ids,feed_id=await self.get_post_ids(user_id,feed_id)
        feed_posts=defaultdict(dict)
        for pool_name,ids in post_ids.items():
            for category_id, p_ids in ids.items():
                if p_ids:
                    feed_posts[pool_name][str(category_id)] = await self.post_svc.get_posts(p_ids)
                else:
                    feed_posts[pool_name][str(category_id)] = []
        
        return feed_posts,feed_id