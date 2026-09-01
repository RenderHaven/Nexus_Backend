from uuid import UUID

from app.domains.user.repository import UserRepository
from app.domains.user.redis import UserRedisStore
from app.domains.user.schemas import User, UserBasic, UserMini


class UserStorage:

    def __init__(self, db, user_repo: UserRepository):
        self.db = db
        self.user_redis_store = UserRedisStore()
        self.user_repo = user_repo

    async def get_author(self, user_id: UUID) -> UserMini | None:
        # TODO: fall back to the database on a cache miss.
        user_data = await self.user_redis_store.get(user_id)
        if user_data:
            return UserMini.model_validate(user_data)
        return None

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
        await self.user_redis_store.set_profile(
            user_id, user_profile.model_dump(mode="json")
        )
        return user_profile

    async def get_category_preferences(self, user_id: UUID) -> dict[str, float] | None:
        # TODO: real preferences; the feed falls back todefaults until then.
        return {}
