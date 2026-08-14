# feed/utils.py

from sqlalchemy import UUID
def get_snapshot_key(pool_name: str, category_id: UUID|str) -> str:
    return f"{pool_name}:{str(category_id)}"