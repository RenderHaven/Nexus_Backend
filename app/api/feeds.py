from fastapi import APIRouter,Depends
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.feed import FeedService
router = APIRouter()

@router.get("/popular")
async def get_popular_post(
    db: AsyncSession = Depends(get_db)
):
    feed_svc = FeedService(db)
    posts = await feed_svc.get_popular_posts(100)
    if not posts:
        return {
            "message": "No posts found"
        }

    return posts


