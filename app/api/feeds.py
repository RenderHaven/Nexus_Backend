from app.schemas.schemas import Feed
from uuid import UUID
from fastapi import APIRouter,Depends
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.feed import FeedService
router = APIRouter()

@router.get("/popular_posts")
async def get_popular_posts(
    offset:int=0,
    db: AsyncSession = Depends(get_db)
):
    feed_svc = FeedService(db)
    posts = await feed_svc.get_popular_posts(offset=offset)
    if not posts:
        return {
            "message": "No posts found"
        }

    return posts
    
# @router.get("/post_ids")
# async def get_post_ids_with_pools(
#     offset:int=0,
#     db: AsyncSession = Depends(get_db)
# ):
#     feed_svc = FeedService(db)
#     post_ids = await feed_svc.get_post_ids_with_pools(offset=offset)
#     if not post_ids:
#         return {
#             "message": "No post ids found"
#         }

#     return post_ids


@router.get("/posts",response_model=Feed)
async def get_popular_post_ids(
    user_id:UUID | None=None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get posts with pools.
    """
    feed_svc = FeedService(db)
    post_ids = await feed_svc.get_posts_with_pools(user_id)
    if not post_ids:
        return {
            "message": "No post ids found"
        }

    return {"posts": post_ids}


