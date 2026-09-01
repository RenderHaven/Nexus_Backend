from uuid import UUID

from fastapi import HTTPException

from app.domains.colleges.pools.user_pool import CollegeUserPool
from app.domains.pool.service import PoolService
from app.domains.colleges.pools.post_pool import CollegePostPool
from app.domains.colleges.repository import CollegeRepository
from app.domains.colleges.storage import CollegeStorage
from app.domains.colleges.schemas import CollegeBasic, CollegeCreate, CollegeUpdate
from app.rules import Permission, require_college_permission, require_permission

class CollegeService:
    def __init__(self, db):
        self.db = db
        self.college_repo = CollegeRepository(db)
        self.storage = CollegeStorage(db)
        self.pool_service = PoolService()

    async def get_college(self, college_id: UUID) -> CollegeBasic | None:
        return await self.storage.get_college(college_id)

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    async def add_college(self, actor, payload: CollegeCreate) -> UUID:
        """
        Create a college. Platform staff only — see app/rules for who that is.
        """
        require_permission(actor, Permission.CREATE_COLLEGE)

        college = await self.college_repo.create(
            payload.model_dump(exclude_unset=True)
        )
        return college.id

    async def edit_college(
        self,
        actor,
        college_id: UUID,
        payload: CollegeUpdate,
    ) -> UUID:
        """
        Change a college's details. Staff only, and college-scoped: a
        moderator or success coach may only edit their own college.

        Only the fields present in the payload are touched.
        """
        require_college_permission(actor, Permission.EDIT_COLLEGE, college_id)

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

    async def get_user_pool_members(self, college_id: UUID, cursor_key: str | None = None, limit: int = 10):
            pool = CollegeUserPool(college_id=college_id, repository=self.college_repo)
            
            pool_members, new_cursor_key = await self.pool_service.get_pool_members(
                group_or_pool=pool,
                cursor_key=cursor_key,
                limit=limit,
                extra_cursor_data={"college_id": str(college_id)}
            )
    
            return pool_members, new_cursor_key
