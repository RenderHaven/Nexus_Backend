"""Response shapes for the Database screen."""
from datetime import datetime

from pydantic import BaseModel, Field


class ConnectionPool(BaseModel):
    """
    Two pools, reported side by side.

    The application pool is SQLAlchemy's, and is what a request actually waits
    on. The server figures come from pg_stat_activity and count every
    connection Postgres has, including psql sessions and any other process
    pointed at this database -- so the two will not match, and the second is
    the one that runs out first.
    """

    reachable: bool = False
    error: str | None = None

    version: str | None = None
    database: str | None = None
    uptime_seconds: int | None = None
    latency_ms: float | None = None

    pool_size: int | None = None
    checked_out: int | None = None
    checked_in: int | None = None
    overflow: int | None = None
    max_overflow: int | None = None
    # checked_out over (size + max_overflow). This is the number that means
    # "requests are about to start queueing".
    pool_saturation_percent: float | None = None

    server_connections: int | None = None
    server_max_connections: int | None = None
    server_saturation_percent: float | None = None
    by_state: dict[str, int] = Field(default_factory=dict)
    # Sessions holding a transaction open without doing anything. These block
    # vacuum and hold locks, and are worth seeing on their own.
    idle_in_transaction: int = 0
    longest_query_seconds: float | None = None


class TableSize(BaseModel):
    table: str
    # From pg_stat_user_tables, which is an estimate maintained by the
    # statistics collector rather than a count. Exact counts would mean a
    # sequential scan per table on every page view.
    estimated_rows: int = 0
    total_bytes: int = 0
    table_bytes: int = 0
    index_bytes: int = 0
    toast_bytes: int = 0
    total_human: str | None = None
    # Rows updated or deleted but not yet vacuumed.
    dead_rows: int = 0
    last_autovacuum: datetime | None = None
    last_autoanalyze: datetime | None = None


class TableReport(BaseModel):
    reachable: bool = False
    error: str | None = None
    database_bytes: int | None = None
    database_human: str | None = None
    tables: list[TableSize] = Field(default_factory=list)


class MigrationStatus(BaseModel):
    script: str
    title: str
    description: str
    applied: bool = False
    # Which specific checks failed, so "pending" says what is actually
    # missing rather than only that something is.
    missing_columns: list[str] = Field(default_factory=list)
    missing_indexes: list[str] = Field(default_factory=list)
    violations: int | None = None
    violations_label: str | None = None


class MigrationReport(BaseModel):
    """
    There is no revision ledger in this project -- migrations are idempotent
    scripts under app/scripts/ and nothing records which have run. Each row
    here is checked against the live schema instead, so `applied` means the
    effect is present, not that someone wrote down that they ran it.
    """

    reachable: bool = False
    error: str | None = None
    uses_revision_ledger: bool = False
    applied: int = 0
    pending: int = 0
    migrations: list[MigrationStatus] = Field(default_factory=list)


class SlowQuery(BaseModel):
    query: str
    calls: int = 0
    total_ms: float = 0.0
    mean_ms: float = 0.0
    max_ms: float | None = None
    rows: int = 0


class SlowQueryReport(BaseModel):
    """
    pg_stat_statements is an extension, and it is not on by default. When it
    is missing the panel says so and how to turn it on, rather than showing an
    empty list that reads like "no slow queries".
    """

    available: bool = False
    enabled: bool = False
    reason: str | None = None
    how_to_enable: str | None = None
    stats_reset: datetime | None = None
    queries: list[SlowQuery] = Field(default_factory=list)


class BackupStatus(BaseModel):
    """
    Whether anything is actually protecting this data.

    Postgres cannot see an external pg_dump on a schedule, so a false here
    means "nothing this database knows about", not a proof of no backups. What
    it can see is WAL archiving, which is the mechanism that would let this
    database be restored to a point in time -- so that is what gets reported,
    honestly, including when it is switched off.
    """

    configured: bool = False
    summary: str | None = None
    archive_mode: str | None = None
    archive_command: str | None = None
    archived_count: int | None = None
    last_archived_at: datetime | None = None
    failed_count: int | None = None
    last_failed_at: datetime | None = None
    stats_reset: datetime | None = None
    healthy: bool | None = None
