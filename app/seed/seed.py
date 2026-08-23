"""
NIAT Nexus — JSON-driven seed loader (schema v5)

Replaces the old raw-SQL seed_v3.sql approach. Seed data now lives as plain
JSON under seeds/data/, one file per table (colleges, users, categories,
posts). post_media is NOT a separate file — each post in posts.json carries
its own `media: [...]` list, which this script unpacks into the post_media
table at insert time. moderation_logs is intentionally skipped for now.

Usage:
    python seed.py
"""
import json
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData, Table

from app.db.model import Base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
DATA_DIR = Path(__file__).parent.parent.parent / "seeds" / "data"

# Table insert order matters: parents before children (FK-safe).
# post_media is derived from posts.json at load time, not its own file.
TABLE_FILES = [
    ("colleges", "colleges.json"),
    ("users", "users.json"),
    ("categories", "categories.json"),
    ("posts", "posts.json"),
]


def load_json(filename: str):
    path = DATA_DIR / filename
    if not path.exists():
        print(f"Warning: {path} not found, skipping.")
        return []
    with open(path) as f:
        return json.load(f)


def prepare_post_rows(raw_posts: list[dict]):
    """
    Split each posts.json entry into (post_row, media_rows).
    The `media` key is not a real posts column — it's peeled off here and
    turned into post_media rows referencing the post's id.
    """
    post_rows = []
    media_rows = []

    for p in raw_posts:
        media_list = p.get("media") or []
        post_row = {k: v for k, v in p.items() if k != "media"}
        post_rows.append(post_row)

        for m in media_list:
            media_rows.append({
                "id": str(uuid.uuid4()),
                "post_id": post_row["id"],
                "url": m["url"],
                "media_type": m.get("media_type", "image"),
                "position": m.get("position", 1),
            })

    return post_rows, media_rows


def seed_db():
    if not DATABASE_URL:
        print("DATABASE_URL not set in environment.")
        return

    engine = create_engine(DATABASE_URL, future=True)

    # Reset schema
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP SCHEMA public CASCADE")
        conn.exec_driver_sql("CREATE SCHEMA public")

    Base.metadata.create_all(engine)

    # Reflect the (now-empty) tables so we can insert generically
    metadata = MetaData()
    metadata.reflect(bind=engine)

    with engine.begin() as conn:
        for table_name, filename in TABLE_FILES:
            rows = load_json(filename)
            if not rows:
                continue

            if table_name == "posts":
                post_rows, media_rows = prepare_post_rows(rows)
                table = Table(table_name, metadata, autoload_with=engine)
                conn.execute(table.insert(), post_rows)
                print(f"  ✅ posts: {len(post_rows)} rows")

                if media_rows:
                    media_table = Table("post_media", metadata, autoload_with=engine)
                    conn.execute(media_table.insert(), media_rows)
                    print(f"  ✅ post_media: {len(media_rows)} rows (derived from posts.json)")
            else:
                table = Table(table_name, metadata, autoload_with=engine)
                conn.execute(table.insert(), rows)
                print(f"  ✅ {table_name}: {len(rows)} rows")

    print("✅ Database seeded successfully from JSON seed data (schema v5).")


if __name__ == "__main__":
    seed_db()