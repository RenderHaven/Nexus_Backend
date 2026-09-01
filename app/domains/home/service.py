"""
Home screen content: trending topics, college news and campus banners.

Nothing here is wired to real data yet. Every method returns a fixed sample so
the API shape is settled and the frontend can build against it; the queries go
in behind these signatures without the endpoints changing.
"""
import uuid
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.domains.home.schemas import Banner, NewsItem, TrendingTopic

# Stable ids so repeated calls look the same to a client that caches by id.
_SAMPLE_NEWS_IDS = [
    UUID("aaaaaaaa-0000-4000-a000-000000000001"),
    UUID("aaaaaaaa-0000-4000-a000-000000000002"),
    UUID("aaaaaaaa-0000-4000-a000-000000000003"),
]

_SAMPLE_BANNER_IDS = [
    UUID("bbbbbbbb-0000-4000-a000-000000000001"),
    UUID("bbbbbbbb-0000-4000-a000-000000000002"),
]


class HomeService:

    def __init__(self, db=None):
        self.db = db

    async def get_trending_topics(self, limit: int = 10) -> list[TrendingTopic]:
        """
        What the platform is talking about right now.

        TODO: derive from recent post volume per category, weighted by
        engagement over a rolling window.
        """
        topics = [
            TrendingTopic(name="Hackathons", post_count=128),
            TrendingTopic(name="Placements", post_count=96),
            TrendingTopic(name="Open Source", post_count=74),
            TrendingTopic(name="Machine Learning", post_count=61),
            TrendingTopic(name="Design Systems", post_count=43),
            TrendingTopic(name="Internships", post_count=37),
            TrendingTopic(name="Robotics", post_count=22),
        ]
        return topics[:limit]

    async def get_news(
        self,
        college_id: UUID | None = None,
        limit: int = 10,
    ) -> list[NewsItem]:
        """
        Announcements for one college, or platform-wide when no college is
        given.

        TODO: read from a news table once it exists; college_id will filter it.
        """
        now = datetime.now(timezone.utc)

        items = [
            NewsItem(
                id=_SAMPLE_NEWS_IDS[0],
                title="Semester project showcase opens for entries",
                summary="Submit your team project before the end of the month.",
                link="https://example.com/showcase",
                college_id=college_id,
                published_at=now - timedelta(hours=6),
            ),
            NewsItem(
                id=_SAMPLE_NEWS_IDS[1],
                title="Campus placement drive announced",
                summary="Twelve companies confirmed for the coming cycle.",
                link="https://example.com/placements",
                college_id=college_id,
                published_at=now - timedelta(days=1),
            ),
            NewsItem(
                id=_SAMPLE_NEWS_IDS[2],
                title="New maker space now open",
                summary="Booking is open to all students from this week.",
                college_id=college_id,
                published_at=now - timedelta(days=3),
            ),
        ]
        return items[:limit]

    async def get_banners(
        self,
        college_id: UUID | None = None,
        limit: int = 5,
    ) -> list[Banner]:
        """
        Campus banners for the top of the home screen.

        TODO: read from a banners table, scoped to the college and to a
        scheduled date range.
        """
        banners = [
            Banner(
                id=_SAMPLE_BANNER_IDS[0],
                title="Founders Week is here",
                image_url="https://plus.unsplash.com/premium_photo-1682310158823-917a4f726802?q=80&w=1212&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D",
                link="https://example.com/founders-week",
                college_id=college_id,
            ),
            Banner(
                id=_SAMPLE_BANNER_IDS[1],
                title="Just dummy 2",
                image_url="https://plus.unsplash.com/premium_photo-1681883455364-b8fc8c56b967?q=80&w=1176&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D",
                link="https://example.com/founders-week",
                college_id=college_id,
            ),
        ]
        return banners[:limit]
