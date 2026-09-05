"""
Add users.is_active and users.updated_at, plus the indexes the admin user
table filters on.

is_active is the reversible alternative to deleting an account: a deactivated
user cannot sign in, and their posts are pulled out of the pools and the
search index.

Safe to run more than once.

Usage:
    PYTHONPATH=. python app/scripts/migrate_user_is_active.py
"""
import asyncio

from sqlalchemy import text

from app.db.session import SessionLocal

STEPS = [
    """
    ALTER TABLE users
        ADD COLUMN IF NOT EXISTS is_active boolean NOT NULL DEFAULT true
    """,
    """
    ALTER TABLE users
        ADD COLUMN IF NOT EXISTS updated_at timestamptz
    """,
    # Existing rows have never been edited, so their last change is their
    # creation.
    """
    UPDATE users
       SET updated_at = created_at
     WHERE updated_at IS NULL
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_users_is_active
        ON users (is_active)
    """,
    # The admin table's main filter: users of one college, narrowed by role.
    """
    CREATE INDEX IF NOT EXISTS ix_users_college_role
        ON users (college_id, role)
    """,
    # `q` searches username; email is already unique-indexed, username is not.
    """
    CREATE INDEX IF NOT EXISTS ix_users_username
        ON users (username)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_users_created_at
        ON users (created_at DESC)
    """,
]


async def run() -> None:
    async with SessionLocal() as db:
        for step in STEPS:
            print(f"-> {' '.join(step.split())[:80]}")
            await db.execute(text(step))
        await db.commit()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(run())
