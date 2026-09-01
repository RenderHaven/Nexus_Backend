from uuid import UUID, uuid4

from fastapi import HTTPException

from app.auth.security import get_password_hash
from app.db.models import User as DBUser
from app.domains.pool.service import PoolService
from app.domains.user.pools.user_post_pool import UserPostPool
from app.domains.user.profile_schemas import UserProfile
from app.domains.user.repository import UserRepository
from app.domains.user.schemas import User, UserBasic, UserCreate, UserMini
from app.domains.user.storage import UserStorage
from app.rules import Permission, require_assignable_role, require_college_permission


class UserService:

    def __init__(self, db):
        self.db = db
        self.user_repo = UserRepository(db)
        self.user_store = UserStorage(db, user_repo=self.user_repo)
        self.pool_service = PoolService()

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def get_author(self, user_id: UUID) -> UserMini | None:
        return await self.user_store.get_author(user_id)

    async def get_user(self, user_id: UUID) -> UserBasic | None:
        return await self.user_store.get_user(user_id)

    async def get_profile(self, user_id: UUID) -> User | None:
        return await self.user_store.get_profile(user_id)

    async def get_category_preferences(
        self,
        user_id: UUID | None = None,
    ) -> dict[str, float] | None:
        if user_id is None:
            return None
        return await self.user_store.get_category_preferences(user_id)

    async def get_pool_members(
        self,
        user_id: UUID,
        cursor_key: str | None = None,
        limit: int = 10,
    ):
        pool = UserPostPool(user_id=user_id, repository=self.user_repo)

        pool_members, new_cursor_key = await self.pool_service.get_pool_members(
            group_or_pool=pool,
            cursor_key=cursor_key,
            limit=limit,
            extra_cursor_data={"user_id": str(user_id)},
        )

        return pool_members, new_cursor_key

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------

    async def update_profile(
        self,
        user_id: UUID,
        profile: UserProfile,
        replace: bool = False,
    ) -> UUID:
        """
        Merge the given fields into the user's profile.

        Only the fields actually present in the payload are touched, so a
        client sending just `about` keeps its skills, education and the rest.
        Pass replace=True to overwrite the whole profile instead.
        """
        db_user = await self.user_repo.get_by_id(user_id)

        if not db_user:
            raise HTTPException(
                status_code=404,
                detail={"code": "user_not_found", "message": "User not found"},
            )

        changes = profile.model_dump(mode="json", exclude_unset=True)

        merged = {} if replace else dict(db_user.profile or {})
        merged.update(changes)

        await self.user_repo.update_profile_json(user_id, merged)
        await self.user_store.user_redis_store.delete(user_id)

        return user_id

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    async def add_user(self, actor, payload: UserCreate) -> UUID:
        """
        Add someone to a college.

        Staff only, and college-scoped: an admin may add a user to any
        college, while a moderator or success coach may only add one to their
        own. Which roles the actor may hand out is decided by app/rules.
        """
        require_college_permission(
            actor,
            Permission.CREATE_USER,
            payload.college_id,
        )
        require_assignable_role(actor, payload.role)

        if not await self.user_repo.college_exists(payload.college_id):
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "college_not_found",
                    "message": "That college does not exist",
                },
            )

        if await self.user_repo.get_by_email(payload.email):
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "email_taken",
                    "message": "An account with that email already exists",
                },
            )

        db_user = DBUser(
            id=uuid4(),
            username=payload.username,
            email=payload.email,
            password=get_password_hash(payload.password),
            college_id=payload.college_id,
            role=payload.role,
            is_alumni=payload.is_alumni,
        )

        created = await self.user_repo.create(db_user)
        return created.id
