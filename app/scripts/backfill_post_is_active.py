"""
One-off backfill for the is_active invariant.

is_active is now derived: a post is publicly visible only while its owner
keeps it published AND a moderator has approved it. Rows created before that
rule was enforced can violate it, so this realigns them and drops the Redis
copies (post cache + pools) that were built from the old values.

Usage:
    PYTHONPATH=. python app/scripts/backfill_post_is_active.py
"""
import asyncio

from sqlalchemy import text

from app.db.session import SessionLocal
from app.redis.client import get_redis

DERIVED = "(status = 'published' AND moderation_status = 'approved')"


async def backfill() -> None:
    async with SessionLocal() as db:
        result = await db.execute(
            text(f"SELECT id FROM posts WHERE is_active <> {DERIVED}")
        )
        post_ids = [str(row[0]) for row in result]

        if not post_ids:
            print("Nothing to backfill; every post already matches the rule.")
            return

        await db.execute(
            text(f"UPDATE posts SET is_active = {DERIVED} WHERE is_active <> {DERIVED}")
        )
        await db.commit()

        print(f"Realigned is_active on {len(post_ids)} post(s).")

    redis = get_redis()

    for post_id in post_ids:
        await redis.delete(f"post:{post_id}")

    pool_keys = [key async for key in redis.scan_iter(match="pool:*")]
    if pool_keys:
        await redis.delete(*pool_keys)

    print(f"Cleared {len(post_ids)} cached post(s) and {len(pool_keys)} pool(s).")


if __name__ == "__main__":
    asyncio.run(backfill())
