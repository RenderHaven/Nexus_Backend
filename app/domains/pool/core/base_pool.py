from app.domains.pool.schemas import PoolObject
from abc import ABC, abstractmethod
class BasePool(ABC):
    pool_name: str
    pool_size:int=100

    refresh_time:int=-1    
    idle_age:int=-1

    @abstractmethod
    async def get_posts(self, db_repo: any) -> list[PoolObject]:
        """Return all posts for this pool."""
        ...

    @abstractmethod
    def score(self, pool_object: PoolObject) -> float:
        """Return the ranking score for a post."""
        ...

    @abstractmethod
    def filter(self, pool_object: PoolObject) -> bool:
        """Return True if the post belongs in this pool."""
        ...