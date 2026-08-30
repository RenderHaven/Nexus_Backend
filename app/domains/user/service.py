from uuid import UUID
from app.domains.pool.service import PoolService
from app.domains.user.pools.user_post_pool import UserPostPool
from app.domains.user.storage import UserStorage
from app.domains.user.repository import UserRepository

class UserService:

    def __init__(self, db):
        self.db = db
        self.user_repo = UserRepository(db)
        self.user_store = UserStorage(db,user_repo=self.user_repo)
        self.pool_service = PoolService()
        
    async def get_user(self, user_id: UUID):
        try:
            return await self.user_store.get_user(user_id)
        except Exception as e:
            raise e

    async def get_profile(self, user_id: UUID):
        try:
            return await self.user_store.get_profile(user_id)
        except Exception as e:
            raise e
    
    async def get_category_preferences(self, user_id: UUID | None = None) -> dict[str, float]:
        try:
            if user_id is None:
                return None
            preferences = await self.user_store.get_category_preferences(user_id)
            return preferences
        except Exception as e:
            raise e

    async def get_pool_members(self, user_id: UUID, cursor_key: str | None = None, limit: int = 10):

        pool = UserPostPool(user_id=user_id, repository=self.user_repo)
        
        pool_members, new_cursor_key = await self.pool_service.get_pool_members(
            group_or_pool=pool,
            cursor_key=cursor_key,
            limit=limit,
            extra_cursor_data={"user_id": str(user_id)}
        )

        return pool_members, new_cursor_key
    async def update_profile(self, user_id: UUID, raw_profile: dict):
        from app.domains.user.profile_schemas import UserProfile
        validated = UserProfile.model_validate(raw_profile)
        await self.user_repo.update_profile_json(user_id, validated.model_dump(mode="json"))
        # Clear redis cache to ensure fresh fetch
        await self.user_store.user_redis_store.delete(user_id)
        return validated
