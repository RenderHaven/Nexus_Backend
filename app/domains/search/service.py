"""
Search across posts, users and colleges.

Not implemented yet: every bucket comes back empty. The shape is settled so
the frontend can build its results screen, and the queries drop in behind
these signatures without the endpoint changing.
"""
from uuid import UUID

from app.domains.search.schemas import SearchResult, SearchScope


class SearchService:

    def __init__(self, db=None):
        self.db = db

    async def get_search(
        self,
        query: str,
        scope: SearchScope = SearchScope.all,
        college_id: UUID | None = None,
        limit: int = 10,
    ) -> SearchResult:
        """
        Look for `query` across every kind of thing, or just one when scope
        narrows it.

        TODO: back each bucket with a real query. Posts should honour
        is_active so hidden posts never surface here; users and colleges can
        match on name. college_id is there to bias or restrict results to one
        campus.
        """
        wants = {
            SearchScope.all,
            scope,
        }

        return SearchResult(
            query=query,
            posts=await self._search_posts(query, college_id, limit)
            if SearchScope.posts in wants or SearchScope.all == scope
            else [],
            users=await self._search_users(query, college_id, limit)
            if SearchScope.users in wants or SearchScope.all == scope
            else [],
            colleges=await self._search_colleges(query, limit)
            if SearchScope.colleges in wants or SearchScope.all == scope
            else [],
        )

    # ------------------------------------------------------------------
    # One bucket each, so they can be filled in independently
    # ------------------------------------------------------------------

    async def _search_posts(
        self,
        query: str,
        college_id: UUID | None,
        limit: int,
    ) -> list:
        # TODO: match on title and content, publicly visible posts only.
        return []

    async def _search_users(
        self,
        query: str,
        college_id: UUID | None,
        limit: int,
    ) -> list:
        # TODO: match on username.
        return []

    async def _search_colleges(self, query: str, limit: int) -> list:
        # TODO: match on name and location.
        return []
