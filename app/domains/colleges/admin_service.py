"""
Staff operations on colleges.

Composes CollegeService for the reads and writes it shares, and owns the
things that need a permission check: the admin table with its counts, the
per-campus stats, the staff roster, and deletion.
"""
from uuid import UUID

from fastapi import HTTPException

from app.domains.colleges.repository import CollegeRepository
from app.domains.colleges.schemas import (
    CollegeAdminRow,
    CollegeStats,
)
from app.domains.colleges.service import CollegeService
from app.domains.colleges.storage import CollegeStorage
from app.rules import Actor, Permission, STAFF_ROLES


class CollegeAdminService:

    def __init__(self, db):
        self.db = db
        self.college_repo = CollegeRepository(db)
        self.storage = CollegeStorage(db)
        self.college_svc = CollegeService(db)

    def _search(self):
        from app.domains.search.service import SearchService

        return SearchService(self.db)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def list_colleges(
        self,
        actor: Actor,
        filters,
        limit: int = 20,
        offset: int = 0,
    ) -> list[CollegeAdminRow]:
        """
        One page of the Manage-Colleges table, with member and post counts.

        An admin sees every college. A moderator or success coach is not
        refused outright -- they get the single row for their own campus, so
        the screen still loads rather than the frontend having to hide a
        whole section.

        The counts come from one grouped query over the page's ids, not a
        pair of counts per row.
        """
        actor.require(Permission.VIEW_COLLEGE_STATS, actor.college_id)

        # None means "every college", which only a platform role reaches.
        only = None if actor.is_platform_wide else actor.college_id

        colleges = await self.college_repo.list_colleges(
            limit=limit,
            offset=offset,
            college_id=only,
            q=filters.q,
            sort=filters.sort.value,
            order=filters.order.value,
        )

        if not colleges:
            return []

        counts = await self.college_repo.counts_for_all([c.id for c in colleges])

        rows = []

        for college in colleges:
            row = CollegeAdminRow.model_validate(college)
            for field, value in counts.get(college.id, {}).items():
                setattr(row, field, value)
            rows.append(row)

        return rows

    async def college_stats(self, actor: Actor, college_id: UUID) -> CollegeStats:
        """Headline numbers for one campus."""
        actor.require(Permission.VIEW_COLLEGE_STATS, college_id)

        if not await self.college_repo.get_college(college_id):
            raise HTTPException(
                status_code=404,
                detail={"code": "college_not_found", "message": "College not found"},
            )

        return CollegeStats(**await self.college_repo.counts_for(college_id))

    async def list_staff(self, actor: Actor, college_id: UUID):
        """
        Who moderates this campus.

        Reuses the people read with a role filter per staff role rather than
        adding a second query that could drift from it.
        """
        actor.require(Permission.VIEW_COLLEGE_STATS, college_id)

        from app.domains.user.schemas import UserBasic

        users = await self.college_repo.get_users(college_id=college_id, limit=200)

        return [
            UserBasic.model_validate(u) for u in users if u.role in STAFF_ROLES
        ]

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def delete_college(self, actor: Actor, college_id: UUID) -> UUID:
        """
        Permanently remove a college. Admin only.

        Refused while anything still points at it. users.college_id and
        posts.college_id are both NOT NULL, so the delete would fail on a
        foreign key regardless; refusing with the counts says why.
        """
        actor.require(Permission.DELETE_COLLEGE, college_id)

        if not await self.college_repo.get_college(college_id):
            raise HTTPException(
                status_code=404,
                detail={"code": "college_not_found", "message": "College not found"},
            )

        refs = await self.college_repo.references(college_id)

        if any(refs.values()):
            # Counts go under `payload`: the error handler passes only code,
            # message and payload through.
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "college_in_use",
                    "message": (
                        "This college still has members or posts and cannot "
                        "be deleted."
                    ),
                    "payload": refs,
                },
            )

        await self.college_repo.delete(college_id)

        await self.storage.invalidate(college_id)
        await self._clear_pools(college_id)
        await self._search().delete_college_search(college_id)

        return college_id

    async def _clear_pools(self, college_id: UUID) -> None:
        """
        Drop the campus's cached pools.

        A deleted college leaves its post and user pools behind otherwise;
        they would sit there until their TTL with rows nothing can resolve.
        """
        from app.redis.client import get_redis
        from app.redis.keys import RedisKeys

        redis = get_redis()

        # Built through RedisKeys.pool, which is what the pools themselves
        # use -- the raw name is only half the key.
        try:
            await redis.delete(
                RedisKeys.pool(f"college:users:{college_id}"),
                RedisKeys.pool(f"college:posts:{college_id}"),
            )
        except Exception:
            # A cache that could not be cleared is stale, not broken -- never
            # fail the delete over it.
            pass
