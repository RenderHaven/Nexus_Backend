from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user_id_optional
from app.db.models import User
from app.db.session import get_db
from app.domains.cursor.service import CursorService
from app.domains.feed.service import FeedService


router = APIRouter()


@router.get("/cursor")
async def get_feed_cursor(
    cursor: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    feed_svc = FeedService(db)

    return await feed_svc.get_feed_cursor(cursor)


@router.post("/delete_cursor")
async def delete_feed_cursor(
    cursor: str | None = None,
):
    cursor_svc = CursorService()

    await cursor_svc.delete_cursor(cursor)

    return {
        "message": "Feed cursor deleted"
    }


# ----------------------------------------------------------------------
# Normal feed
# ----------------------------------------------------------------------

@router.get("/groups")
async def get_feed_groups(
    db: AsyncSession = Depends(get_db),
):
    feed_svc = FeedService(db)

    groups = feed_svc.get_feed_groups()

    return {
        "groups": groups
    }


@router.get("/post_ids/{grp_name}")
async def get_feed_post_ids(
    grp_name: str,
    user_id: User | None = Depends(
        get_current_user_id_optional
    ),
    cursor: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    feed_svc = FeedService(db)

    post_ids, next_cursor = await feed_svc.get_post_ids(
        grp_name,
        user_id,
        cursor,
    )

    if not post_ids:
        return {
            "posts": [],
            "next_cursor": None,
        }

    return {
        "posts": post_ids,
        "next_cursor": next_cursor,
    }

