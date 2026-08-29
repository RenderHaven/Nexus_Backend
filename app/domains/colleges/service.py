from uuid import UUID
from app.domains.colleges.pools.user_pool import CollegeUserPool
from app.domains.pool.service import PoolService
from app.domains.colleges.pools.post_pool import CollegePostPool
from app.domains.colleges.repository import CollegeRepository
from app.domains.colleges.storage import CollegeStorage
from app.domains.colleges.schemas import CollegeBasic

class CollegeService:
    def __init__(self, db):
        self.db = db
        self.college_repo = CollegeRepository(db)
        self.storage = CollegeStorage(db)
        self.pool_service = PoolService()

    async def get_college(self, college_id: UUID) -> CollegeBasic | None:
        return await self.storage.get_college(college_id)


    async def get_post_pool_members(self, college_id: UUID, cursor_key: str | None = None, limit: int = 10):
        pool = CollegePostPool(college_id=college_id, repository=self.college_repo)
        
        pool_members, new_cursor_key = await self.pool_service.get_pool_members(
            group_or_pool=pool,
            cursor_key=cursor_key,
            limit=limit,
            extra_cursor_data={"college_id": str(college_id)}
        )

        return pool_members,new_cursor_key 

    async def get_user_pool_members(self, college_id: UUID, cursor_key: str | None = None, limit: int = 10):
            pool = CollegeUserPool(college_id=college_id, repository=self.college_repo)
            
            pool_members, new_cursor_key = await self.pool_service.get_pool_members(
                group_or_pool=pool,
                cursor_key=cursor_key,
                limit=limit,
                extra_cursor_data={"college_id": str(college_id)}
            )
    
            return pool_members, new_cursor_key
