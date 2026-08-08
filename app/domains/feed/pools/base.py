from app.schemas.schemas import PostSmall
from abc import ABC, abstractmethod
from typing import Any


class BasePool(ABC):
    pool_name: str
    pool_size:int=500

    def __init__(self, pool_probablity: int= 50):
        self.pool_probablity = pool_probablity

    @abstractmethod
    async def get_posts(self, db_repo: any) -> list[PostSmall]:
        """Return all posts for this pool."""
        ...

    @abstractmethod
    def score(self, pool_post: PostSmall) -> float:
        """Return the ranking score for a post."""
        ...

    @abstractmethod
    def filter(self, pool_post: PostSmall) -> bool:
        """Return True if the post belongs in this pool."""
        ...