from uuid import UUID
from app.schemas.schemas import PostResponse
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.post import PostService
from app.db.session import get_db
router = APIRouter()


@router.get(
    "/top-engagement",
    response_model=list[PostResponse],
)
async def get_top_engagement_posts(
    limit: int =10,
    db: AsyncSession = Depends(get_db),
):
    post_service = PostService(db)

    posts = await post_service.get_posts_by_engagement(limit)

    return posts

@router.get("/{id}",response_model=PostResponse)
async def get_post(id:UUID,db:AsyncSession=Depends(get_db)):
    post_svc = PostService(db)    
    post = await post_svc.get_post(id)
    if not post:
        return {
            "message": "No posts found"
        }
    return post

