from fastapi import APIRouter
from app.api.posts import router as post_router
from app.api.comments import router as comments_router
from app.api.feeds import router as feeds_router

from app.api.users import router as user_router
from app.api.colleges import router as colleges_router
from app.api.categories import router as categories_router
from app.api.media import router as media_router
from app.auth import router as auth_router
from app.api.chats import router as chats_router
from app.api.collabs import router as collabs_router
from app.api.home import router as home_router
from app.api.search import router as search_router
from app.api.admin import router as admin_router
from app.api.infra import router as infra_router
api_router = APIRouter()

api_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["Auth"],
)

api_router.include_router(
    admin_router,
    prefix="/admin",
    tags=["Admin"],
)

api_router.include_router(
    home_router,
    prefix="/home",
    tags=["Home"],
)

api_router.include_router(
    search_router,
    prefix="/search",
    tags=["Search"],
)

api_router.include_router(
    user_router,
    prefix="/users",
    tags=["Users"],
)

api_router.include_router(
    colleges_router,
    prefix="/colleges",
    tags=["Colleges"],
)

api_router.include_router(
    categories_router,
    prefix="/categories",
    tags=["Categories"],
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

api_router.include_router(
    collabs_router,
    prefix="/collabs",
    tags=["Collaborations"],
)

api_router.include_router(
    comments_router,
    prefix="/comments",
    tags=["Comments"],
)

api_router.include_router(
    media_router,
    prefix="/media",
    tags=["Media"],
)

api_router.include_router(
    chats_router,
    prefix="/chats",
    tags=["Chats"],
)

api_router.include_router(
    infra_router,
    prefix="/infra",
    tags=["Infrastructure"],
)
