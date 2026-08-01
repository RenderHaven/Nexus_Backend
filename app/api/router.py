from fastapi import APIRouter
from app.api.posts import router as post_router
from app.api.redis import router as redis_router
from app.api.feeds import router as feeds_router

api_router = APIRouter()

api_router.include_router(
    post_router,
    prefix="/posts",
    tags=["Posts"],
)

api_router.include_router(
    redis_router,
    prefix="/redis",
    tags=["Debug"],
)

api_router.include_router(
    feeds_router,
    prefix="/feeds",
    tags=["Feeds"],
)