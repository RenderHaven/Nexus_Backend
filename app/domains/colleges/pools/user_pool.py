from uuid import UUID
from app.domains.user.pools.user_pool import BaseUserPool
from app.domains.user.schemas import UserPoolObject

class CollegeUserPool(BaseUserPool):
    def __init__(self, college_id: UUID, repository):
        self.college_id = college_id
        self.repository = repository
        self.pool_name = f"college:users:{college_id}"

    async def get_users(self) -> list[UserPoolObject]:
        users = await self.repository.get_users(
            college_id=self.college_id,
            limit=self.pool_size,
        )
        return [UserPoolObject.model_validate(user) for user in users]

    def filter(self, user: UserPoolObject) -> bool:
        return user.is_active

    def score(self, user: UserPoolObject) -> float:
        return user.created_at.timestamp()
