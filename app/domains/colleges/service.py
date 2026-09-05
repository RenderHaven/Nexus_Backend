from uuid import UUID

from fastapi import HTTPException

from app.domains.colleges.pools.user_pool import CollegeUserPool
from app.domains.pool.service import PoolService
from app.domains.colleges.pools.post_pool import CollegePostPool
from app.domains.colleges.repository import CollegeRepository
from app.domains.colleges.storage import CollegeStorage
from app.domains.colleges.schemas import CollegeBasic, CollegeCreate, CollegeUpdate
from app.rules import Actor, Permission

class CollegeService:
    def __init__(self, db):
        self.db = db
        self.college_repo = CollegeRepository(db)
        self.storage = CollegeStorage(db)
        self.pool_service = PoolService()

    async def get_college(self, college_id: UUID) -> CollegeBasic | None:
        return await self.storage.get_college(college_id)

    async def get_colleges_by_id(
        self,
        college_ids: list[UUID],
    ) -> dict[UUID, CollegeBasic]:
        """Batch id -> college, for hydrating a list of posts or users."""
        return await self.storage.get_colleges_by_id(college_ids)

    async def get_colleges(self) -> list[CollegeBasic]:
        """
        Every college, straight from the database.

        Deliberately uncached: the per-college keys behind get_college are
        invalidated one id at a time, so a cached whole-list would need its
        own invalidation on every create and edit and would be the thing that
        goes stale. The table is small and this is a cold-path read.
        """
        return await self.college_repo.get_colleges()

    async def _reindex(self, college_id: UUID) -> None:
        """Best effort by construction -- SearchService logs and swallows its
        own failures, so a search outage never fails a college write."""
        from app.domains.search.service import SearchService

        await SearchService(self.db).update_college_search(college_id)

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    async def add_college(self, actor: Actor, payload: CollegeCreate) -> UUID:
        """
        Create a college. Platform staff only — see app/rules for who that is.
        """
        actor.require(Permission.CREATE_COLLEGE)

        college = await self.college_repo.create(
            payload.model_dump(exclude_unset=True)
        )

        await self._reindex(college.id)

        return college.id

    async def edit_college(
        self,
        actor: Actor,
        college_id: UUID,
        payload: CollegeUpdate,
    ) -> UUID:
        """
        Change a college's details. Staff only, and college-scoped: a
        moderator or success coach may only edit their own college.

        Only the fields present in the payload are touched.
        """
        actor.require(Permission.EDIT_COLLEGE, college_id)

        changes = payload.model_dump(exclude_unset=True)

        if not changes:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "nothing_to_update",
                    "message": "No fields were given to change",
                },
            )

        updated_id = await self.college_repo.update(college_id, changes)

        if not updated_id:
            raise HTTPException(
                status_code=404,
                detail={"code": "college_not_found", "message": "College not found"},
            )

        await self.storage.invalidate(college_id)
        await self._reindex(college_id)

        return updated_id


    async def get_post_pool_members(self, college_id: UUID, cursor_key: str | None = None, limit: int = 10):
        pool = CollegePostPool(college_id=college_id, repository=self.college_repo)
        
        pool_members, new_cursor_key = await self.pool_service.get_pool_members(
            group_or_pool=pool,
            cursor_key=cursor_key,
            limit=limit,
            extra_cursor_data={"college_id": str(college_id)}
        )

        return pool_members,new_cursor_key 

    async def get_user_pool_members(
        self,
        college_id: UUID,
        cursor_key: str | None = None,
        limit: int = 10,
    ):
        """
        One page of a campus's people.

        Takes the college as a parameter rather than reading it off the
        caller, so the same method serves "my college" and any other campus's
        People tab. Deactivated accounts are filtered out in the repository.
        """
        pool = CollegeUserPool(college_id=college_id, repository=self.college_repo)

        pool_members, new_cursor_key = await self.pool_service.get_pool_members(
            group_or_pool=pool,
            cursor_key=cursor_key,
            limit=limit,
            extra_cursor_data={"college_id": str(college_id)},
        )

        return pool_members, new_cursor_key

    async def get_people(
        self,
        college_id: UUID,
        filters=None,
        limit: int = 20,
    ):
        """
        A campus's people, filtered by role, alumni status or name.

        Straight from the repository rather than the pool: the pool is a
        single unfiltered ranking, and building one per filter combination
        would be a cache key per query string.
        """
        from app.domains.user.schemas import UserBasic

        users = await self.college_repo.get_users(
            college_id=college_id,
            limit=limit,
            role=getattr(filters, "role", None),
            is_alumni=getattr(filters, "is_alumni", None),
            q=getattr(filters, "q", None),
        )
        return [UserBasic.model_validate(u) for u in users]
