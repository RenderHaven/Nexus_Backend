from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.auth.deps import get_current_user_optional
from app.db.models import User
from app.domains.home.schemas import Banner, NewsItem, TrendingTopic
from app.domains.home.service import HomeService

router = APIRouter()


def _college_for(
    college_id: UUID | None,
    current_user: User | None,
) -> UUID | None:
    """Fall back to the signed-in person's own college when none is named."""
    if college_id is not None:
        return college_id
    return current_user.college_id if current_user else None


@router.get("/trending_topics", response_model=list[TrendingTopic])
async def get_trending_topics(
    limit: int = Query(10, ge=1, le=50),
):
    """What the platform is talking about right now, most active first."""
    return await HomeService().get_trending_topics(limit=limit)


@router.get("/news", response_model=list[NewsItem])
async def get_news(
    college_id: UUID | None = None,
    limit: int = Query(10, ge=1, le=50),
    current_user: User | None = Depends(get_current_user_optional),
):
    """Announcements for a college, newest first.

    Defaults to your own college when you are signed in and no college is
    named."""
    return await HomeService().get_news(
        college_id=_college_for(college_id, current_user),
        limit=limit,
    )


@router.get("/banners", response_model=list[Banner])
async def get_banners(
    college_id: UUID | None = None,
    limit: int = Query(5, ge=1, le=20),
    current_user: User | None = Depends(get_current_user_optional),
):
    """Campus banners for the top of the home screen.

    Defaults to your own college when you are signed in and no college is
    named."""
    return await HomeService().get_banners(
        college_id=_college_for(college_id, current_user),
        limit=limit,
    )
