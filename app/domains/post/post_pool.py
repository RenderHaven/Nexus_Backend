from abc import abstractmethod

from app.domains.pool.core.base_pool import BasePool
from app.domains.post.schemas import PostPoolObject,PostPoolMember


class BasePostPool(BasePool):

    async def get_objects(self) -> list[PostPoolObject]:
        """
        Return posts that can be considered by this pool.
        """
        return await self.get_posts()

    def to_member(self, post: PostPoolObject) -> PostPoolMember:
        """
        Convert a PostPoolObject into the lightweight member
        stored inside Redis.
        """
        return PostPoolMember(
            id=post.id,
            type=post.type,
            created_at=post.created_at,
        )

    @classmethod
    def member_type(cls) -> type[PostPoolMember]:
        return PostPoolMember

    @abstractmethod
    async def get_posts(self) -> list[PostPoolObject]:
        """
        Return posts used to build this pool.
        """
        ...