from app.domains.pool.core.pool_post import PoolPost
from abc import ABC, abstractmethod
class BasePool(ABC):
    pool_name: str
    pool_size:int=100

    @abstractmethod
    async def get_posts(self, db_repo: any) -> list[PoolPost]:
        """Return all posts for this pool."""
        ...

    @abstractmethod
    def score(self, pool_post: PoolPost) -> float:
        """Return the ranking score for a post."""
        ...

    @abstractmethod
    def filter(self, pool_post: PoolPost) -> bool:
        """Return True if the post belongs in this pool."""
        ...