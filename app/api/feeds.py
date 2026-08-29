from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user_id_optional
from app.db.models import User
from app.db.session import get_db
from app.domains.cursor.service import CursorService
from app.domains.feed.service import FeedService
from app.schemas.common import Paginated
from app.domains.post.schemas import PostPoolMember


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


@router.get("/post_items/{grp_name}", response_model=Paginated[PostPoolMember])
async def get_feed_pool_members(
    grp_name: str,
    user_id: User | None = Depends(
        get_current_user_id_optional
    ),
    cursor: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    feed_svc = FeedService(db)

    pool_members, next_cursor = await feed_svc.get_pool_members(
        grp_name,
        user_id,
        cursor,
    )

    if not pool_members:
        return {
            "items": [],
            "next_cursor": None,
        }

    return {
        "items": pool_members,
        "next_cursor": next_cursor,
    }

