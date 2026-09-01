"""
Add post_media.public_id.

The Cloudinary id is what lets us move or remove a file when its post is taken
down; without it we only have the delivery URL. Existing rows seeded from
external image hosts have no Cloudinary id, so the column is nullable.

Safe to run more than once.

Usage:
    PYTHONPATH=. python app/scripts/migrate_post_media_public_id.py
"""
import asyncio

from sqlalchemy import text

from app.db.session import SessionLocal


async def migrate() -> None:
    async with SessionLocal() as db:
        exists = (
            await db.execute(
                text(
                    """
                    SELECT 1 FROM information_schema.columns
                     WHERE table_name = 'post_media' AND column_name = 'public_id'
                    """
                )
            )
        ).scalar()

        if exists:
            print("Already migrated; nothing to do.")
            return

        await db.execute(text("ALTER TABLE post_media ADD COLUMN public_id text"))
        await db.commit()

        total = (await db.execute(text("SELECT count(*) FROM post_media"))).scalar()
        print(f"Added post_media.public_id ({total} existing row(s) left null).")


if __name__ == "__main__":
    asyncio.run(migrate())
