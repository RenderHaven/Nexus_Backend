"""
Infrastructure monitoring.

One section per piece of infrastructure the app reads through, each backed by
a service that lives next to the thing it monitors -- the cache one is
app/redis/service.py. Search and database get the same treatment under
/infra/search and /infra/database when their services exist.

Administrators only. VIEW_INFRASTRUCTURE and MANAGE_INFRASTRUCTURE are both
PLATFORM_ROLES, which is `{admin}` -- a moderator or success coach is staff
for their own campus and gets 403 here, the same as a student.

The read permission is declared on the router rather than on each route, so a
route added to this file is guarded whether or not its author remembers to ask
for it. Routes that write (cache invalidation, search reindex) then narrow
further to MANAGE_INFRASTRUCTURE on top of that; a route can only ever tighten
what the router already requires, never loosen it.

Not college-scoped: there is one Redis, one cluster and one database, so there
is no per-campus view of them to scope to.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_actor
from app.db.schemas import (
    BackupStatus,
    ConnectionPool,
    MigrationReport,
    SlowQueryReport,
    TableReport,
)
from app.db.service import DatabaseMonitorService
from app.db.session import get_db
from app.domains.search.opensearch.schemas import (
    IngestLag,
    MappingReport,
    QueryResult,
    ReindexReport,
    ReindexState,
    SearchHealth,
)
from app.domains.search.opensearch.service import SearchMonitorService
from app.redis.schemas import (
    CacheHealth,
    HitRate,
    InvalidationResult,
    KeyInspection,
    KeyspaceReport,
    TTLPolicy,
)
from app.redis.service import RedisMonitorService
from app.rules import Actor, Permission

async def get_infra_reader(actor: Actor = Depends(get_actor)) -> Actor:
    """Read access to every infrastructure screen. Administrators only."""
    actor.require(Permission.VIEW_INFRASTRUCTURE)
    return actor


async def get_infra_admin(actor: Actor = Depends(get_actor)) -> Actor:
    """Anything that changes infrastructure state: invalidate, reindex."""
    actor.require(Permission.MANAGE_INFRASTRUCTURE)
    return actor


# The read check sits on the router, so it applies to every route in this file
# including ones added later. Write routes add get_infra_admin on top.
router = APIRouter(dependencies=[Depends(get_infra_reader)])


# ----------------------------------------------------------------------
# Cache engine
# ----------------------------------------------------------------------

@router.get("/cache/health", response_model=CacheHealth)
async def cache_health(actor: Actor = Depends(get_infra_reader)):
    """
    Reachability, memory in use, evictions and uptime.

    Returns 200 with reachable=false when Redis is down, rather than an error:
    the screen needs to render the outage, not inherit it.
    """
    return await RedisMonitorService().health()


@router.get("/cache/hit_rate", response_model=HitRate)
async def cache_hit_rate(
    hours: int = Query(24, ge=1, le=168),
    actor: Actor = Depends(get_infra_reader),
):
    """
    Hits against misses over time, server-wide and per key namespace.

    The server-wide pair is Redis's own counter and covers every key it has
    been asked for since it started. The per-namespace pair is ours, recorded
    by the entity caches as they read, and covers only those.
    """
    return await RedisMonitorService().hit_rate(hours=hours)


@router.get("/cache/keyspace", response_model=KeyspaceReport)
async def cache_keyspace(actor: Actor = Depends(get_infra_reader)):
    """
    Key counts and sampled TTL/size per namespace.

    A bounded SCAN -- `truncated` says whether it stopped early, in which case
    the counts are a floor.
    """
    return await RedisMonitorService().keyspace()


@router.get("/cache/key", response_model=KeyInspection)
async def cache_key(
    key: str = Query(..., min_length=1, max_length=512),
    actor: Actor = Depends(get_infra_reader),
):
    """
    Look up one key and see what is actually stored: type, TTL, size and a
    truncated preview of the value.

    Taken as a query parameter rather than a path segment because cache keys
    contain colons and slashes.
    """
    return await RedisMonitorService().inspect(key)


@router.get("/cache/ttl_policy", response_model=TTLPolicy)
async def cache_ttl_policy(actor: Actor = Depends(get_infra_reader)):
    """
    What each namespace is declared to expire after, next to what its live
    keys say. The disagreement column is the point.
    """
    return await RedisMonitorService().ttl_policy()


@router.delete("/cache/key", response_model=InvalidationResult)
async def invalidate_cache_key(
    key: str = Query(..., min_length=1, max_length=512),
    actor: Actor = Depends(get_infra_admin),
):
    """Drop one key. The next read reloads it from Postgres."""
    return await RedisMonitorService().invalidate_key(key)


@router.delete("/cache/namespace/{namespace}", response_model=InvalidationResult)
async def invalidate_cache_namespace(
    namespace: str,
    actor: Actor = Depends(get_infra_admin),
):
    """
    Drop every key in one namespace.

    The namespace must be one named in app/redis/namespaces.py, so no caller
    can pass a pattern that sweeps the whole keyspace. Deleting is safe by
    construction -- every read path treats a miss as "load from Postgres" --
    but it is not free: a busted post namespace means the next feed page is
    served entirely from the database.
    """
    try:
        return await RedisMonitorService().invalidate_namespace(namespace)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "invalid_namespace", "message": str(exc)},
        )


# ----------------------------------------------------------------------
# Search engine
# ----------------------------------------------------------------------

@router.get("/search/health", response_model=SearchHealth)
async def search_health(actor: Actor = Depends(get_infra_reader)):
    """
    Cluster status, shard state and document counts per index.

    `configured: false` when OPENSEARCH_URL is unset -- a supported way to run
    this app, so it is reported as a state rather than an error.
    """
    return await SearchMonitorService().health()


@router.get("/search/ingest_lag", response_model=IngestLag)
async def search_ingest_lag(
    actor: Actor = Depends(get_infra_reader),
    db: AsyncSession = Depends(get_db),
):
    """
    How far each index trails its source table.

    A negative drift is the one to worry about: it means the index holds
    documents the database no longer has, which is a failed delete leaving
    removed content searchable.
    """
    return await SearchMonitorService(db).ingest_lag()


@router.get("/search/mappings", response_model=MappingReport)
async def search_mappings(actor: Actor = Depends(get_infra_reader)):
    """
    What each field is indexed as and how text is tokenised, with the live
    mapping compared against the one in opensearch/indexes.py. A drift there
    means a rebuild is owed.
    """
    return await SearchMonitorService().mappings()


@router.get("/search/query", response_model=QueryResult)
async def search_query(
    index: str = Query(..., description="posts, users or colleges"),
    q: str = Query(..., min_length=1, max_length=500),
    size: int = Query(10, ge=1, le=50),
    actor: Actor = Depends(get_infra_reader),
):
    """
    Run a query and see the raw hits and scores behind a result.

    Unfiltered on purpose: this shows what the index holds, not what the
    public endpoint would return.
    """
    return await SearchMonitorService().run_query(index, q, size=size)


@router.get("/search/reindex", response_model=ReindexReport)
async def search_reindex_status(actor: Actor = Depends(get_infra_reader)):
    """The state of the most recent rebuild of each index."""
    return await SearchMonitorService().reindex_status()


@router.post("/search/reindex/{index}", response_model=ReindexState, status_code=202)
async def start_search_reindex(
    index: str,
    actor: Actor = Depends(get_infra_admin),
):
    """
    Rebuild one index from Postgres.

    Returns 202 immediately and runs in the background -- a full rebuild walks
    every row of the source table, well past any HTTP timeout. Poll
    GET /infra/search/reindex for the outcome.

    Safe while search is live: the rebuild fills a fresh version alongside the
    current one and only swaps the alias once the new index holds everything
    that was read.
    """
    try:
        return await SearchMonitorService().start_reindex(
            index,
            triggered_by=str(actor.id),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "reindex_refused", "message": str(exc)},
        )


# ----------------------------------------------------------------------
# Database
# ----------------------------------------------------------------------

@router.get("/database/pool", response_model=ConnectionPool)
async def database_pool(
    actor: Actor = Depends(get_infra_reader),
    db: AsyncSession = Depends(get_db),
):
    """
    Open connections, waiters and pool saturation.

    Two pools side by side: SQLAlchemy's, which is what a request waits on,
    and the server's from pg_stat_activity, which counts every connection
    Postgres has and is the one that runs out first.
    """
    return await DatabaseMonitorService(db).pool()


@router.get("/database/tables", response_model=TableReport)
async def database_tables(
    actor: Actor = Depends(get_infra_reader),
    db: AsyncSession = Depends(get_db),
):
    """
    Row counts and on-disk size per table, largest first.

    Counts are the statistics collector's estimate, not SELECT count(*) --
    exact counts would be one sequential scan per table per page view.
    """
    return await DatabaseMonitorService(db).tables()


@router.get("/database/migrations", response_model=MigrationReport)
async def database_migrations(
    actor: Actor = Depends(get_infra_reader),
    db: AsyncSession = Depends(get_db),
):
    """
    Which migrations are applied.

    There is no revision ledger in this project -- migrations are idempotent
    scripts under app/scripts/ and nothing records which have run. Each is
    checked against the live schema instead, so `applied` means the effect is
    present rather than that someone wrote down that they ran it.
    """
    return await DatabaseMonitorService(db).migrations()


@router.get("/database/slow_queries", response_model=SlowQueryReport)
async def database_slow_queries(
    limit: int = Query(20, ge=1, le=100),
    actor: Actor = Depends(get_infra_reader),
    db: AsyncSession = Depends(get_db),
):
    """
    The statements costing the most total time, from pg_stat_statements.

    Ordered by total time, not mean: a 5ms query run a million times is a
    bigger problem than a 5s query run twice. When the extension is not
    installed the response says so rather than returning an empty list that
    reads like "nothing is slow".
    """
    return await DatabaseMonitorService(db).slow_queries(limit=limit)


@router.get("/database/backups", response_model=BackupStatus)
async def database_backups(
    actor: Actor = Depends(get_infra_reader),
    db: AsyncSession = Depends(get_db),
):
    """
    When the last backup ran and whether it succeeded.

    Only WAL archiving is visible from inside Postgres, so a negative here
    means "nothing this database knows about", not that no backups exist.
    """
    return await DatabaseMonitorService(db).backups()
