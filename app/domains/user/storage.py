from uuid import UUID

from app.domains.user.repository import UserRepository
from app.domains.user.redis import UserRedisStore
from app.schemas.schemas import User


class UserStorage:

    def __init__(self, db):
        self.user_redis_store = UserRedisStore()
        self.user_repo = UserRepository(db)

    async def get_user(self, user_id: UUID) -> User | None:
        user = await self.user_redis_store.get(user_id)

        if user:
            return User.model_validate(user)

        db_user = await self.user_repo.get_by_id(user_id)

        if not db_user:
            return None

        user = User.model_validate(db_user)

        await self.user_redis_store.set(
            user.id,
            user.model_dump(mode="json")
        )

        return user
    
    async def get_category_preferences(self, user_id: UUID) -> dict[str,int] | None:
        return {}