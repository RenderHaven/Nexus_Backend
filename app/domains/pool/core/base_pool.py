from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from app.domains.pool.schemas import PoolMember, PoolObject


class BasePool(ABC):
    pool_name: str
    pool_size: int = 100

    refresh_time: int = -1
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