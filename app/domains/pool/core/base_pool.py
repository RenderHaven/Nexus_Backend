from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from app.domains.pool.schemas import PoolMember, PoolObject

TObject = TypeVar("TObject", bound=PoolObject)
TMember = TypeVar("TMember", bound=PoolMember)


class BasePool(ABC, Generic[TObject, TMember]):
    pool_name: str
    pool_size: int = 100

    refresh_time: int = -1
    idle_age: int = -1

    @abstractmethod
    async def get_objects(self) -> list[TObject]:
        ...

    @abstractmethod
    def score(self, obj: TObject) -> float:
        ...

    @abstractmethod
    def filter(self, obj: TObject) -> bool:
        ...

    @abstractmethod
    def to_member(self, obj: TObject) -> TMember:
        ...

    @classmethod
    @abstractmethod
    def member_type(cls) -> type[TMember]:
        ...