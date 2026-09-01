from abc import abstractmethod

from app.domains.pool.core.base_pool import BasePool
from app.domains.user.schemas import UserPoolObject,UserPoolMember


class BaseUserPool(BasePool):

    async def get_objects(self) -> list[UserPoolObject]:
        """
        Return the users that can be considered by this pool.
        """
        return await self.get_users()

    def to_member(self, user: UserPoolObject) -> UserPoolMember:
        """
        Convert a UserPoolObject into the lightweight member stored inside
        Redis. Every field the member declares is carried across, so a
        listing never reports a stale default in place of the real value.
        """
        return UserPoolMember(
            id=user.id,
            college_id=user.college_id,
            username=user.username,
            role=user.role,
            is_alumni=user.is_alumni,
            created_at=user.created_at,
        )

    @classmethod
    def member_type(cls) -> type[UserPoolMember]:
        return UserPoolMember

    @abstractmethod
    async def get_users(self) -> list[UserPoolObject]:
        """
        Return the users this pool is built from.
        """
        ...