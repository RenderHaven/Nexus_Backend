from fastapi import APIRouter
from app.api.posts import router as post_router
from app.api.redis import router as redis_router
from app.api.feeds import router as feeds_router
from app.api.categories import router as category_router
from app.api.users import router as user_router
from app.auth import router as auth_router

api_router = APIRouter()

api_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["Auth"],
)

api_router.include_router(
    user_router,
    prefix="/users",
    tags=["Users"],
)

api_router.include_router(
    feeds_router,
    prefix="/feeds",
    tags=["Feeds"],
)

api_router.include_router(
    post_router,
    prefix="/posts",
    tags=["Posts"],
)

# api_router.include_router(
#     redis_router,
#     prefix="/redis",
#     tags=["Debug"],
# )

api_router.include_router(
    category_router,
    prefix="/category",
    tags=["Categories"],
)