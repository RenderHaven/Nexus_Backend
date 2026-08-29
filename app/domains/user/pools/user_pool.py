from abc import abstractmethod

from app.domains.pool.core.base_pool import BasePool
from app.domains.user.schemas import UserPoolObject,UserPoolMember


class BaseUserPool(BasePool):

    async def get_objects(self) -> list[UserPoolObject]:
        """
        Return posts that can be considered by this pool.
        """
        return await self.get_users()

    def to_member(self, post: UserPoolObject) -> UserPoolMember:
        """
        Convert a PostPoolObject into the lightweight member
        stored inside Redis.
        """
        return UserPoolMember(
            id=post.id,
            college_id=post.college_id,
            username=post.username,
            created_at=post.created_at,
        )

    @classmethod
    def member_type(cls) -> type[UserPoolMember]:
        return UserPoolMember

    @abstractmethod
    async def get_users(self) -> list[UserPoolObject]:
        """
        Return posts used to build this pool.
        """
        ...