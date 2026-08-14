from app.domains.feed.feed_snapshot.service import FeedSnapshotService
from app.schemas.schemas import Feed
from uuid import UUID
from fastapi import APIRouter,Depends
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.feed.service import FeedService
router = APIRouter()


@router.get("/feed_snapshot")
async def get_feed_snapshot(
    feed_id:UUID|None=None,
    db: AsyncSession = Depends(get_db),
):
    feed_svc = FeedService(db)
    feed_snapshot=await feed_svc.get_feed_snapshot(feed_id)
    return feed_snapshot

@router.post("/delete_feed_snapshot")
async def delete_feed_snapshot(
    feed_id:UUID|None=None,
):
    feed_snapshot_svc=FeedSnapshotService()
    await feed_snapshot_svc.delete_snapshot(feed_id)
    return {"message": "Feed snapshot deleted"}
    

@router.get("/posts",response_model=Feed)
async def get_pool_posts(
    user_id:str|None=None,
    feed_id:UUID|None=None,
    db: AsyncSession = Depends(get_db),
):
    feed_svc = FeedService(db)
    if user_id is not None:
        user_id = UUID(user_id)
    post_ids,feed_id = await feed_svc.get_posts(user_id,feed_id)
    if not post_ids:
        return {
            "message": "No post ids found"
        }

    return {"posts": post_ids,"feed_id":feed_id}

@router.get("/post_ids")
async def get_pool_posts(
    user_id:str|None=None,
    feed_id:UUID|None=None,
    db: AsyncSession = Depends(get_db),
):
    feed_svc = FeedService(db)
    if user_id is not None:
        user_id = UUID(user_id)
    post_ids,feed_id = await feed_svc.get_post_ids(user_id,feed_id)
    if not post_ids:
        return {
            "message": "No post ids found"
        }

    return {"posts": post_ids,"feed_id":feed_id}


