from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from .schemas import CollegeBasic
from .repository import CollegeRepository
from .redis import CollegeRedisStore
from app.redis import metrics

class CollegeStorage:
    def __init__(self, db: AsyncSession):
        self.repository = CollegeRepository(db)
        self.redis_store = CollegeRedisStore()

    async def invalidate(self, college_id: UUID) -> None:
        await self.redis_store.delete_college(college_id)

    async def get_colleges_by_id(
        self,
        college_ids: list[UUID],
    ) -> dict[UUID, CollegeBasic]:
        """
        Resolve a batch of college ids for hydrating a list.

        Per-id even though the table is small: hydrating a page of twenty
        posts wants the three or four colleges that appear on it, not the
        whole table. The unpaginated whole-table read stays get_colleges(),
        for the callers that genuinely asked for everything.
        """
        if not college_ids:
            return {}

        unique_ids = list(dict.fromkeys(college_ids))
        cached = await self.redis_store.get_many(unique_ids)

        result: dict[UUID, CollegeBasic] = {}
        missing: list[UUID] = []

        for college_id, college in zip(unique_ids, cached):
            if college:
                result[college_id] = college
            else:
                missing.append(college_id)

        await metrics.record("college", hits=len(result), misses=len(missing))

        if missing:
            rows = await self.repository.colleges_by_ids(missing)
            for college in rows:
                result[college.id] = college
            await self.redis_store.set_many(rows)

        return result

    async def get_college(self, college_id: UUID) -> CollegeBasic | None:
        college = await self.redis_store.get_college(college_id)
        if college:
            await metrics.record("college", hits=1)
            return college

        await metrics.record("college", misses=1)

        college = await self.repository.get_college(college_id)
        if college:
            await self.redis_store.set_college(college)
        return college
