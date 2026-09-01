from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from app.domains.pool.schemas import PoolMember, PoolObject


# How long a pool may serve cached members before it is rebuilt from source.
DEFAULT_REFRESH_TIME = 8 * 60 * 60


class BasePool(ABC):
    pool_name: str
    pool_size: int = 100

    # refresh_time: rebuild this long after the pool was built.
    # idle_age: expire this long after the pool was last read (sliding window).
    # A pool that wants the sliding behaviour sets idle_age and clears
    # refresh_time, since refresh_time takes precedence when both are set.
    refresh_time: int = DEFAULT_REFRESH_TIME
    idle_age: int = -1

    @abstractmethod
    async def get_objects(self) -> list[PoolObject]:
        ...

    @abstractmethod
    def score(self, obj: PoolObject) -> float:
        ...

    @abstractmethod
    def filter(self, obj: PoolObject) -> bool:
        ...

    @abstractmethod
    def to_member(self, obj: PoolObject) -> PoolMember:
        ...

    @classmethod
    @abstractmethod
    def member_type(cls) -> type[PoolMember]:
        ...