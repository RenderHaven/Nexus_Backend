"""
NIAT Nexus — JSON-driven seed loader (schema v6)

Comments are loaded from seeds/data/comments.json after posts. Root comments
are inserted before replies because post_comments.parent_id is a
self-referencing foreign key.

Usage:
    python seed.py
"""
import json
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData, Table, text

from app.db.models import Base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
DATA_DIR = Path(__file__).parent.parent.parent / "seeds" / "data"

TABLE_FILES = [
    ("colleges", "colleges.json"),
    ("users", "users.json"),
    ("categories", "categories.json"),
    ("posts", "posts.json"),
    ("post_comments", "comments.json"),
]


# =========================
# Special seed user
# =========================

VIKRAM_USER_ID = "00000000-0000-0000-0000-000000001002"
NIAT_JAIPUR_COLLEGE_ID = "00000000-0000-0000-0000-000000009001"


def seed_special_user(conn, metadata):
    """
    Create the special development/test user and their college.

    This user is used by comments.json and other development seed data.
    """

    college_table = Table(
        "colleges",
        metadata,
        autoload_with=conn,
    )

    user_table = Table(
        "users",
        metadata,
        autoload_with=conn,
    )

    # ---------------------------------
    # NIAT Jaipur
    # ---------------------------------

    college = {
        "id": NIAT_JAIPUR_COLLEGE_ID,
        "name": "NIAT Jaipur",
        "about": "NIAT Jaipur development seed college.",
    }

    conn.execute(
        college_table.insert(),
        college,
    )

    # ---------------------------------
    # Vikram
    # ---------------------------------

    user = {
        "id": VIKRAM_USER_ID,
        "college_id": NIAT_JAIPUR_COLLEGE_ID,
        "username": "vikram",
        "email": "vikram1002@gmail.com",
        "password": "password123",
        "role": "student",
        "is_alumni": False,
        "total_xp": 0,
        "current_level": "spark",
        "profile": {
            "name": "Vikram",
            "bio": "Student at NIAT Jaipur.",
            "headline": "Computer Science Student",
            "location": "Jaipur",
        },
    }

    conn.execute(
        user_table.insert(),
        user,
    )

    print("  ✅ special college: NIAT Jaipur")
    print("  ✅ special user: vikram")


def load_json(filename: str):
    path = DATA_DIR / filename
    if not path.exists():
        print(f"Warning: {path} not found, skipping.")
        return []

    with open(path, encoding="utf-8") as f:
        return json.load(f)


def prepare_post_rows(raw_posts: list[dict]):
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


def prepare_comment_rows(raw_comments: list[dict]):
    """
    Split comments into root comments and replies.

    Root comments have parent_id=None. Replies are inserted after their
    parents so the self-referencing foreign key is satisfied.
    """
    root_comments = [
        c for c in raw_comments
        if c.get("parent_id") is None
    ]

    replies = [
        c for c in raw_comments
        if c.get("parent_id") is not None
    ]

    return root_comments, replies


def seed_comments(conn, metadata, raw_comments: list[dict]):
    """
    Insert comments and maintain the denormalized counters:
      - posts.comment_count
      - post_comments.reply_count
    """
    if not raw_comments:
        return

    comment_table = Table(
        "post_comments",
        metadata,
        autoload_with=conn,
    )

    root_comments, replies = prepare_comment_rows(raw_comments)

    # Parents first.
    if root_comments:
        conn.execute(comment_table.insert(), root_comments)
        print(f"  ✅ post_comments: {len(root_comments)} root comments")

    # Children second.
    if replies:
        conn.execute(comment_table.insert(), replies)
        print(f"  ✅ post_comments: {len(replies)} replies")

    # Maintain reply_count on each parent comment.
    reply_counts = {}
    for reply in replies:
        parent_id = reply["parent_id"]
        reply_counts[parent_id] = reply_counts.get(parent_id, 0) + 1

    for parent_id, count in reply_counts.items():
        conn.execute(
            text(
                """
                UPDATE post_comments
                SET reply_count = reply_count + :count
                WHERE id = :parent_id
                """
            ),
            {
                "count": count,
                "parent_id": parent_id,
            },
        )

    # Maintain comment_count on each affected post.
    post_counts = {}
    for comment in raw_comments:
        post_id = comment["post_id"]
        post_counts[post_id] = post_counts.get(post_id, 0) + 1

    for post_id, count in post_counts.items():
        conn.execute(
            text(
                """
                UPDATE posts
                SET comment_count = comment_count + :count
                WHERE id = :post_id
                """
            ),
            {
                "count": count,
                "post_id": post_id,
            },
        )

    print(f"  ✅ updated comment_count for {len(post_counts)} posts")
    print(f"  ✅ updated reply_count for {len(reply_counts)} comments")


def seed_db():
    if not DATABASE_URL:
        print("DATABASE_URL not set in environment.")
        return

    engine = create_engine(DATABASE_URL, future=True)

    # Reset schema.
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP SCHEMA public CASCADE")
        conn.exec_driver_sql("CREATE SCHEMA public")

    Base.metadata.create_all(engine)

    metadata = MetaData()
    metadata.reflect(bind=engine)

    with engine.begin() as conn:
        seed_special_user(conn, metadata)
        
        for table_name, filename in TABLE_FILES:
            rows = load_json(filename)
            if not rows:
                continue

            if table_name == "posts":
                post_rows, media_rows = prepare_post_rows(rows)

                table = Table(
                    table_name,
                    metadata,
                    autoload_with=conn,
                )

                conn.execute(table.insert(), post_rows)
                print(f"  ✅ posts: {len(post_rows)} rows")

                if media_rows:
                    media_table = Table(
                        "post_media",
                        metadata,
                        autoload_with=conn,
                    )
                    conn.execute(media_table.insert(), media_rows)
                    print(
                        f"  ✅ post_media: {len(media_rows)} rows "
                        f"(derived from posts.json)"
                    )

            elif table_name == "post_comments":
                seed_comments(conn, metadata, rows)

            else:
                table = Table(
                    table_name,
                    metadata,
                    autoload_with=conn,
                )
                conn.execute(table.insert(), rows)
                print(f"  ✅ {table_name}: {len(rows)} rows")

    print("✅ Database seeded successfully from JSON seed data (schema v6).")


if __name__ == "__main__":
    seed_db()