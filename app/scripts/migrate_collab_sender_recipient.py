"""
Split collaboration_requests.user_id into sender_id and recipient_id.

sender_id is who asked to join; recipient_id is the post's author, who decides.
Existing rows keep their requester as sender_id and take recipient_id from the
post they point at.

Safe to run more than once.

Usage:
    PYTHONPATH=. python app/scripts/migrate_collab_sender_recipient.py
"""
import asyncio

from sqlalchemy import text

from app.db.session import SessionLocal

STEPS = [
    # 1. rename the old column to its new meaning
    """
    ALTER TABLE collaboration_requests
        RENAME COLUMN user_id TO sender_id
    """,
    # 2. add the other side, nullable for now so the backfill can run
    """
    ALTER TABLE collaboration_requests
        ADD COLUMN recipient_id uuid REFERENCES users(id)
    """,
    # 3. every existing request was addressed to the author of its post
    """
    UPDATE collaboration_requests cr
       SET recipient_id = p.user_id
      FROM posts p
     WHERE p.id = cr.post_id
       AND cr.recipient_id IS NULL
    """,
    # 4. now it can be required
    """
    ALTER TABLE collaboration_requests
        ALTER COLUMN recipient_id SET NOT NULL
    """,
    # 5. one request per person per post, and an index for each direction
    """
    ALTER TABLE collaboration_requests
        ADD CONSTRAINT uq_collab_requests_post_sender UNIQUE (post_id, sender_id)
    """,
    """
    CREATE INDEX idx_collab_requests_sender
        ON collaboration_requests (sender_id, created_at)
    """,
    """
    CREATE INDEX idx_collab_requests_recipient
        ON collaboration_requests (recipient_id, created_at)
    """,
]


async def column_exists(db, column: str) -> bool:
    result = await db.execute(
        text(
            """
            SELECT 1 FROM information_schema.columns
             WHERE table_name = 'collaboration_requests'
               AND column_name = :c
            """
        ),
        {"c": column},
    )
    return result.scalar() is not None


async def migrate() -> None:
    async with SessionLocal() as db:
        if await column_exists(db, "sender_id") and await column_exists(db, "recipient_id"):
            print("Already migrated; nothing to do.")
            return

        rows = (
            await db.execute(text("SELECT count(*) FROM collaboration_requests"))
        ).scalar()
        print(f"Migrating collaboration_requests ({rows} existing row(s))...")

        for step in STEPS:
            try:
                await db.execute(text(step))
            except Exception as exc:
                # Re-running after a partial migration should not be fatal.
                print(f"  skipped: {str(exc).splitlines()[0]}")
                await db.rollback()
                continue

        await db.commit()

        orphans = (
            await db.execute(
                text("SELECT count(*) FROM collaboration_requests WHERE recipient_id IS NULL")
            )
        ).scalar()

        print(f"Done. Rows without a recipient: {orphans}")


if __name__ == "__main__":
    asyncio.run(migrate())
