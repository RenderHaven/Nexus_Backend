"""
Search across posts, users and colleges.

Two halves, deliberately in one place because they share the mapping:

  Reads   -- OpenSearch matches and ranks, and returns nothing but ids. The
             documents themselves are hydrated from the entity cache, so a
             search result and a feed card are built by the same code and can
             never disagree about a username.

  Writes  -- update_*_search / delete_*_search keep the indices in step with
             Postgres. Every one of them is best effort: a search cluster that
             is down, slow or unconfigured must never fail a user's write. The
             rebuild script is what repairs the drift that causes.
"""

import asyncio
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.search.documents import (
    college_document,
    post_document,
    user_document,
)
from app.domains.search.opensearch import SearchIndexes, get_opensearch, is_configured
from app.domains.search.opensearch.admin import ensure_all
from app.domains.search.schemas import SearchResult, SearchScope
from app.rules import Actor

logger = logging.getLogger(__name__)


class SearchService:

    def __init__(self, db: AsyncSession | None = None):
        self.db = db

        # Each domain owns the read that feeds its own index. The search
        # domain owns only the shape of the document built from it.
        if db is not None:
            from app.domains.colleges.repository import CollegeRepository
            from app.domains.post.repository import PostRepository
            from app.domains.user.repository import UserRepository

            self.post_repo = PostRepository(db)
            self.user_repo = UserRepository(db)
            self.college_repo = CollegeRepository(db)

    # ------------------------------------------------------------------
    # Index writes
    #
    # None of these raise. An index that misses an update shows a stale or
    # missing search hit; a write that fails because the search cluster
    # hiccuped is a broken product.
    # ------------------------------------------------------------------

    async def _upsert(self, index_name: str, doc_id: UUID | str, doc: dict) -> bool:
        if not is_configured():
            return False
        try:
            await get_opensearch().index(
                index=SearchIndexes.alias(index_name),
                id=str(doc_id),
                body=doc,
            )
            return True
        except Exception:
            logger.exception("search upsert failed: %s/%s", index_name, doc_id)
            return False

    async def _delete(self, index_name: str, doc_id: UUID | str) -> bool:
        if not is_configured():
            return False
        try:
            await get_opensearch().delete(
                index=SearchIndexes.alias(index_name),
                id=str(doc_id),
                ignore=[404],
            )
            return True
        except Exception:
            logger.exception("search delete failed: %s/%s", index_name, doc_id)
            return False

    async def update_post_search(self, post_id: UUID) -> bool:
        """
        Bring one post's search document in line with the database.

        Only publicly visible posts are indexed. A post that is gone, deleted,
        archived, or still waiting on moderation is removed from the index
        rather than stored with a flag, so nothing a reader may not see is
        ever held there. That makes this one call the whole lifecycle:
        approving a post inserts it, holding or archiving it deletes it.
        """
        if not is_configured():
            return False

        try:
            row = await self.post_repo.get_post_row(post_id)
        except Exception:
            logger.exception("search: could not read post %s", post_id)
            return False

        if row is None or not row.is_active:
            return await self._delete(SearchIndexes.POSTS, post_id)

        return await self._upsert(SearchIndexes.POSTS, post_id, post_document(row))

    async def delete_post_search(self, post_id: UUID) -> bool:
        return await self._delete(SearchIndexes.POSTS, post_id)

    async def update_user_search(self, user_id: UUID) -> bool:
        """
        Bring one user's search document in line with the database.

        A deactivated account is removed from the index rather than stored
        with a flag, exactly as a hidden post is: their content is already
        pulled from the feed, so leaving the person findable would be an
        odd half-measure. Reactivating puts them back.
        """
        if not is_configured():
            return False

        try:
            row = await self.user_repo.get_user_row(user_id)
        except Exception:
            logger.exception("search: could not read user %s", user_id)
            return False

        if row is None or not getattr(row, "is_active", True):
            return await self._delete(SearchIndexes.USERS, user_id)

        return await self._upsert(SearchIndexes.USERS, user_id, user_document(row))

    async def delete_user_search(self, user_id: UUID) -> bool:
        return await self._delete(SearchIndexes.USERS, user_id)

    async def update_college_search(self, college_id: UUID) -> bool:
        if not is_configured():
            return False

        try:
            row = await self.college_repo.get_college_row(college_id)
        except Exception:
            logger.exception("search: could not read college %s", college_id)
            return False

        if row is None:
            return await self._delete(SearchIndexes.COLLEGES, college_id)

        return await self._upsert(
            SearchIndexes.COLLEGES, college_id, college_document(row)
        )

    async def delete_college_search(self, college_id: UUID) -> bool:
        return await self._delete(SearchIndexes.COLLEGES, college_id)

    async def ensure_indexes(self) -> None:
        """Create any missing index and alias so queries answer (emptily)
        instead of erroring against a fresh cluster."""
        if is_configured():
            await ensure_all()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def _search_ids(self, index_name: str, body: dict) -> list[UUID]:
        """Run one query and return matching ids in relevance order.

        `_source: False` keeps documents off the wire entirely -- the index
        matches, the entity cache renders.
        """
        if not is_configured():
            return []

        try:
            response = await get_opensearch().search(
                index=SearchIndexes.alias(index_name),
                body={"_source": False, **body},
            )
        except Exception:
            logger.exception("search query failed on %s", index_name)
            return []

        ids = []
        for hit in response.get("hits", {}).get("hits", []):
            try:
                ids.append(UUID(hit["_id"]))
            except (ValueError, KeyError):
                continue

        return ids

    async def get_search(
        self,
        query: str,
        scope: SearchScope = SearchScope.all,
        college_id: UUID | None = None,
        limit: int = 10,
        actor: "Actor | None" = None,
    ) -> SearchResult:
        """
        Look for `query` across every kind of thing, or just one when scope
        narrows it.

        The buckets are independent, so they run concurrently and a failure in
        one comes back empty rather than taking the whole response down.
        """
        wants_posts = scope in (SearchScope.all, SearchScope.posts)
        wants_users = scope in (SearchScope.all, SearchScope.users)
        wants_colleges = scope in (SearchScope.all, SearchScope.colleges)

        posts, users, colleges = await asyncio.gather(
            self._search_posts(query, college_id, limit, actor)
            if wants_posts
            else _empty(),
            self._search_users(query, college_id, limit) if wants_users else _empty(),
            self._search_colleges(query, limit) if wants_colleges else _empty(),
        )

        return SearchResult(
            query=query,
            posts=posts,
            users=users,
            colleges=colleges,
        )

    # ------------------------------------------------------------------
    # One bucket each: match in OpenSearch, hydrate from the entity cache
    # ------------------------------------------------------------------

    async def _search_posts(
        self,
        query: str,
        college_id: UUID | None,
        limit: int,
        actor: "Actor | None" = None,
    ) -> list:
        from app.domains.post.schemas import PostBasic
        from app.domains.post.service import PostService

        # Forced, never caller-controlled: only active posts are indexed, and
        # this filter makes sure a stale document left behind by a failed
        # delete still cannot reach a reader.
        filters: list[dict] = [{"term": {"is_active": True}}]
        if college_id is not None:
            filters.append({"term": {"college_id": str(college_id)}})

        ids = await self._search_ids(
            SearchIndexes.POSTS,
            {
                "size": limit,
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["title^3", "content"],
                                    "fuzziness": "AUTO",
                                }
                            }
                        ],
                        "filter": filters,
                    }
                },
            },
        )

        if not ids:
            return []

        posts = await PostService(self.db).get_posts(ids, actor)
        return [PostBasic.model_validate(p, from_attributes=True) for p in posts]

    async def _search_users(
        self,
        query: str,
        college_id: UUID | None,
        limit: int,
    ) -> list:
        from app.domains.user.service import UserService

        filters: list[dict] = []
        if college_id is not None:
            filters.append({"term": {"college_id": str(college_id)}})

        ids = await self._search_ids(
            SearchIndexes.USERS,
            {
                "size": limit,
                "query": {
                    "bool": {
                        "must": [{"match": {"username": {"query": query}}}],
                        "filter": filters,
                    }
                },
            },
        )

        if not ids:
            return []

        user_svc = UserService(self.db)
        users = await asyncio.gather(*(user_svc.get_user(uid) for uid in ids))
        return [u for u in users if u is not None]

    async def _search_colleges(self, query: str, limit: int) -> list:
        from app.domains.colleges.storage import CollegeStorage

        ids = await self._search_ids(
            SearchIndexes.COLLEGES,
            {
                "size": limit,
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["name^3", "location", "tagline"],
                        "fuzziness": "AUTO",
                    }
                },
            },
        )

        if not ids:
            return []

        storage = CollegeStorage(self.db)
        colleges = await asyncio.gather(*(storage.get_college(cid) for cid in ids))
        return [c for c in colleges if c is not None]


async def _empty() -> list:
    return []
