"""
Indexes for the moderation queue and its audit trail.

The queue filters on (college, status) and orders by created_at or
reviewed_at; the history and activity feed read moderation_logs by post and
by moderator. Without these, every tab of the review screen is a sequential
scan of posts.

Safe to run more than once.

Usage:
    PYTHONPATH=. python app/scripts/migrate_moderation_indexes.py
"""
import asyncio

from sqlalchemy import text

from app.db.session import SessionLocal

STEPS = [
    # The moderation queue: filter by college + status, order by arrival.
    """
    CREATE INDEX IF NOT EXISTS ix_posts_moderation_queue
        ON posts (college_id, moderation_status, created_at DESC)
    """,
    # sort=reviewed_at, and the time-to-decision stat.
    """
    CREATE INDEX IF NOT EXISTS ix_posts_reviewed_at
        ON posts (reviewed_at DESC)
        WHERE reviewed_at IS NOT NULL
    """,
    # "posts by this author in the queue".
    """
    CREATE INDEX IF NOT EXISTS ix_posts_user_moderation
        ON posts (user_id, moderation_status)
    """,
    # One post's decision history, newest first.
    """
    CREATE INDEX IF NOT EXISTS ix_moderation_logs_post
        ON moderation_logs (post_id, created_at DESC)
    """,
    # Decisions per moderator, and the activity feed.
    """
    CREATE INDEX IF NOT EXISTS ix_moderation_logs_coach
        ON moderation_logs (coach_id, created_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_moderation_logs_created_at
        ON moderation_logs (created_at DESC)
    """,
]


async def run() -> None:
    async with SessionLocal() as db:
        for step in STEPS:
            name = " ".join(step.split())[:80]
            print(f"-> {name}")
            await db.execute(text(step))
        await db.commit()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(run())
