from app.domains.pool.core.pool_config import PoolConfig


class PoolGroup:
    group_name: str
    pools: list[PoolConfig]