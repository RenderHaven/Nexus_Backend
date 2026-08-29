from app.domains.pool.core.base_pool import BasePool


class PoolConfig:
    pool: BasePool
    weight: float

class PoolGroup:
    group_name: str
    pools: list[PoolConfig]