from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from .schemas import CollegeBasic
from .repository import CollegeRepository
from .redis import CollegeRedisStore

class CollegeStorage:
    def __init__(self, db: AsyncSession):
        self.repository = CollegeRepository(db)
        self.redis_store = CollegeRedisStore()

    async def invalidate(self, college_id: UUID) -> None:
        await self.redis_store.delete_college(college_id)

    async def get_college(self, college_id: UUID) -> CollegeBasic | None:
        college = await self.redis_store.get_college(college_id)
        if college:
            return college
        
        college = await self.repository.get_college(college_id)
        if college:
            await self.redis_store.set_college(college)
        return college
