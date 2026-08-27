from uuid import UUID
from app.domains.pool.service import PoolService
from app.domains.colleges.pools.college_post_pool import CollegePostPool
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


    async def get_post_ids(self, college_id: UUID, cursor_key: str | None = None, limit: int = 10):
        pool = CollegePostPool(college_id=college_id, repository=self.college_repo)
        
        post_ids, new_cursor_key = await self.pool_service.get_post_ids(
            group_or_pool=pool,
            cursor_key=cursor_key,
            limit=limit,
            extra_cursor_data={"college_id": str(college_id)}
        )

        return post_ids, new_cursor_key
