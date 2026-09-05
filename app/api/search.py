from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_actor_optional
from app.db.session import get_db
from app.domains.search.schemas import SearchResult, SearchScope
from app.domains.search.service import SearchService
from app.rules import Actor

router = APIRouter()


@router.get("", response_model=SearchResult)
async def get_search(
    q: str = Query(..., min_length=1, max_length=200, description="What to look for"),
    scope: SearchScope = SearchScope.all,
    college_id: UUID | None = None,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    actor: Actor = Depends(get_actor_optional),
):
    """Search posts, people and colleges at once.

    Results come back in three buckets, each always present. Narrow with scope
    to search only one kind of thing, or pass college_id to focus on one
    campus.

    Signing in is optional; it only decides whether post hits come back with
    is_liked filled in."""
    return await SearchService(db).get_search(
        query=q,
        scope=scope,
        college_id=college_id,
        limit=limit,
        actor=actor,
    )
