from uuid import UUID

from app.domains.pool.service import PoolService
from app.domains.user.pools.user_post_pool import UserPostPool
from app.domains.user.repository import UserRepository
from app.domains.user.redis import UserRedisStore
from app.schemas.schemas import User
from app.domains.user.domain import UserBasic


class UserStorage:

    def __init__(self, db,user_repo:UserRepository):
        self.user_redis_store = UserRedisStore()
        self.user_repo = user_repo
        self.pool_service=PoolService()
        self.post_pool=UserPostPool(db,repository=self.user_repo)

    async def get_user(self, user_id: UUID) -> UserBasic | None:
        user_data = await self.user_redis_store.get(user_id)
        if user_data:
            return UserBasic.model_validate(user_data)

        db_user = await self.user_repo.get_by_id(user_id)
        if not db_user:
            return None
        
        user_basic = UserBasic.model_validate(db_user)
        await self.user_redis_store.set(user_id, user_basic.model_dump(mode="json"))
        return user_basic

    async def get_profile(self, user_id: UUID) -> User | None:
        profile_data = await self.user_redis_store.get_profile(user_id)
        if profile_data:
            return User.model_validate(profile_data)

        db_user = await self.user_repo.get_by_id(user_id)
        if not db_user:
            return None

        user_profile = User.model_validate(db_user)
        await self.user_redis_store.set_profile(user_id, user_profile.model_dump(mode="json"))
        return user_profile
    
    async def get_category_preferences(self, user_id: UUID) -> dict[str,float] | None:
        return {}

    async def get_post_ids(self,user_id:UUID,offsets)->list[UUID]:
        pass