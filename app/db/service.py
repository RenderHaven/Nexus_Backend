"""
Monitoring for Postgres.

This is the source of truth: everything the cache and the search index hold is
derived from here, so when the three disagree this is the one that is right.
The screen it backs answers five questions -- is the pool saturated, what is
big, is the schema where the code expects it, what is slow, and is anything
backing it up.

Same three rules as the cache monitor (see INFRA_MONITORING.md):

  * Bounded work only. Row counts come from the statistics collector, never
    from SELECT count(*) per table -- an admin page view must not sequentially
    scan every table in the database.
  * Degrade, never raise. Every method reports reachable=false with the error
    rather than propagating it.
  * Read-only. Nothing here writes, and nothing here runs caller-supplied SQL.
"""
import time
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import engine
from app.db.migrations import MIGRATIONS
from app.db.schemas import (
    BackupStatus,
    ConnectionPool,
    MigrationReport,
    MigrationStatus,
    SlowQuery,
    SlowQueryReport,
    TableReport,
    TableSize,
)

# Rows returned by the two list panels. Both are ordered, so this is a top-N
# rather than a truncation that hides the interesting rows.
TABLE_LIMIT = 50
SLOW_QUERY_LIMIT = 20

# Longest statement text handed back. pg_stat_statements normalises queries but
# an IN list can still be enormous.
QUERY_PREVIEW = 2000


class DatabaseMonitorService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Connection pool
    # ------------------------------------------------------------------

    async def pool(self) -> ConnectionPool:
        started = time.perf_counter()

        try:
            await self.db.execute(text("SELECT 1"))
            latency_ms = round((time.perf_counter() - started) * 1000, 3)
        except Exception as exc:
            return ConnectionPool(
                reachable=False, error=f"{type(exc).__name__}: {exc}"
            )

        report = ConnectionPool(reachable=True, latency_ms=latency_ms)

        # The application pool. QueuePool exposes these; NullPool and the
        # async fallbacks do not, hence the guarded reads rather than
        # attribute access.
        pool = engine.pool
        for field, method in (
            ("pool_size", "size"),
            ("checked_out", "checkedout"),
            ("checked_in", "checkedin"),
            ("overflow", "overflow"),
        ):
            reader = getattr(pool, method, None)
            if callable(reader):
                try:
                    setattr(report, field, int(reader()))
                except Exception:
                    pass

        max_overflow = getattr(pool, "_max_overflow", None)
        if isinstance(max_overflow, int):
            report.max_overflow = max_overflow

        # SQLAlchemy counts overflow from -pool_size, so it is negative until
        # the base pool is full. Reported as 0 rather than -4, which reads as
        # a bug to anyone looking at the screen.
        if report.overflow is not None:
            report.overflow = max(0, report.overflow)

        if report.pool_size is not None and report.checked_out is not None:
            capacity = report.pool_size + (report.max_overflow or 0)
            if capacity > 0:
                report.pool_saturation_percent = round(
                    report.checked_out / capacity * 100, 2
                )

        try:
            row = (
                await self.db.execute(
                    text(
                        """
                        SELECT version(),
                               current_database(),
                               extract(epoch from (now() - pg_postmaster_start_time()))
                        """
                    )
                )
            ).one()
            report.version = row[0]
            report.database = row[1]
            report.uptime_seconds = int(row[2] or 0)

            report.server_max_connections = int(
                (
                    await self.db.execute(text("SHOW max_connections"))
                ).scalar_one()
            )

            states = (
                await self.db.execute(
                    text(
                        """
                        SELECT coalesce(state, 'unknown'), count(*)
                          FROM pg_stat_activity
                         WHERE datname = current_database()
                      GROUP BY 1
                        """
                    )
                )
            ).all()
            report.by_state = {state: int(count) for state, count in states}
            report.server_connections = sum(report.by_state.values())
            report.idle_in_transaction = report.by_state.get(
                "idle in transaction", 0
            ) + report.by_state.get("idle in transaction (aborted)", 0)

            if report.server_max_connections:
                report.server_saturation_percent = round(
                    report.server_connections / report.server_max_connections * 100,
                    2,
                )

            longest = (
                await self.db.execute(
                    text(
                        """
                        SELECT max(extract(epoch from (now() - query_start)))
                          FROM pg_stat_activity
                         WHERE datname = current_database()
                           AND state = 'active'
                           AND pid <> pg_backend_pid()
                        """
                    )
                )
            ).scalar_one_or_none()
            report.longest_query_seconds = (
                round(float(longest), 3) if longest is not None else None
            )
        except Exception as exc:
            report.error = f"{type(exc).__name__}: {exc}"

        return report

    # ------------------------------------------------------------------
    # Table sizes
    # ------------------------------------------------------------------

    async def tables(self) -> TableReport:
        """
        Row counts and on-disk size per table, largest first.

        estimated_rows is n_live_tup from the statistics collector, not a
        count -- exact counts would be one sequential scan per table per page
        view. It drifts between autovacuum runs, which is why the last
        autovacuum time is reported next to it.
        """
        try:
            rows = (
                await self.db.execute(
                    text(
                        """
                        SELECT c.relname,
                               s.n_live_tup,
                               s.n_dead_tup,
                               pg_total_relation_size(c.oid),
                               pg_table_size(c.oid),
                               pg_indexes_size(c.oid),
                               coalesce(pg_total_relation_size(c.reltoastrelid), 0),
                               pg_size_pretty(pg_total_relation_size(c.oid)),
                               s.last_autovacuum,
                               s.last_autoanalyze
                          FROM pg_class c
                          JOIN pg_namespace n ON n.oid = c.relnamespace
                     LEFT JOIN pg_stat_user_tables s ON s.relid = c.oid
                         WHERE c.relkind = 'r'
                           AND n.nspname = 'public'
                      ORDER BY pg_total_relation_size(c.oid) DESC
                         LIMIT :limit
                        """
                    ),
                    {"limit": TABLE_LIMIT},
                )
            ).all()

            size = (
                await self.db.execute(
                    text(
                        "SELECT pg_database_size(current_database()), "
                        "pg_size_pretty(pg_database_size(current_database()))"
                    )
                )
            ).one()
        except Exception as exc:
            return TableReport(reachable=False, error=f"{type(exc).__name__}: {exc}")

        return TableReport(
            reachable=True,
            database_bytes=int(size[0]),
            database_human=size[1],
            tables=[
                TableSize(
                    table=row[0],
                    estimated_rows=int(row[1] or 0),
                    dead_rows=int(row[2] or 0),
                    total_bytes=int(row[3] or 0),
                    table_bytes=int(row[4] or 0),
                    index_bytes=int(row[5] or 0),
                    toast_bytes=int(row[6] or 0),
                    total_human=row[7],
                    last_autovacuum=row[8],
                    last_autoanalyze=row[9],
                )
                for row in rows
            ],
        )

    # ------------------------------------------------------------------
    # Migration status
    # ------------------------------------------------------------------

    async def migrations(self) -> MigrationReport:
        """
        Whether each migration script's effect is present in the live schema.

        Not a revision ledger -- there isn't one. See app/db/migrations.py for
        why checking the schema is the better answer here, and for the table
        this walks.
        """
        try:
            columns = {
                (row[0], row[1])
                for row in (
                    await self.db.execute(
                        text(
                            "SELECT table_name, column_name FROM information_schema.columns "
                            "WHERE table_schema = 'public'"
                        )
                    )
                ).all()
            }
            indexes = {
                row[0]
                for row in (
                    await self.db.execute(
                        text(
                            "SELECT indexname FROM pg_indexes WHERE schemaname = 'public'"
                        )
                    )
                ).all()
            }
        except Exception as exc:
            return MigrationReport(
                reachable=False, error=f"{type(exc).__name__}: {exc}"
            )

        statuses = []

        for migration in MIGRATIONS:
            missing_columns = [
                f"{table}.{column}"
                for table, column in migration.columns
                if (table, column) not in columns
            ]
            missing_indexes = [
                index for index in migration.indexes if index not in indexes
            ]

            violations = None
            if migration.violations_sql:
                try:
                    violations = int(
                        (
                            await self.db.execute(text(migration.violations_sql))
                        ).scalar_one()
                        or 0
                    )
                except Exception:
                    # A backfill whose check cannot run is not evidence that
                    # the backfill is done.
                    violations = None

            applied = (
                not missing_columns
                and not missing_indexes
                and (violations == 0 if migration.violations_sql else True)
            )

            statuses.append(
                MigrationStatus(
                    script=migration.script,
                    title=migration.title,
                    description=migration.description,
                    applied=applied,
                    missing_columns=missing_columns,
                    missing_indexes=missing_indexes,
                    violations=violations,
                    violations_label=migration.violations_label,
                )
            )

        applied_count = sum(1 for s in statuses if s.applied)

        return MigrationReport(
            reachable=True,
            uses_revision_ledger=False,
            applied=applied_count,
            pending=len(statuses) - applied_count,
            migrations=statuses,
        )

    # ------------------------------------------------------------------
    # Slow queries
    # ------------------------------------------------------------------

    async def slow_queries(self, limit: int = SLOW_QUERY_LIMIT) -> SlowQueryReport:
        """
        The statements costing the most total time, from pg_stat_statements.

        Ordered by total time rather than mean: a 5ms query run a million times
        is a bigger problem than a 5s query run twice, and only the first
        ordering finds it.
        """
        how_to_enable = (
            "Add pg_stat_statements to shared_preload_libraries in "
            "postgresql.conf, restart Postgres, then run "
            "CREATE EXTENSION pg_stat_statements;"
        )

        try:
            available = bool(
                (
                    await self.db.execute(
                        text(
                            "SELECT 1 FROM pg_available_extensions "
                            "WHERE name = 'pg_stat_statements'"
                        )
                    )
                ).scalar_one_or_none()
            )
            installed = bool(
                (
                    await self.db.execute(
                        text("SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'")
                    )
                ).scalar_one_or_none()
            )
        except Exception as exc:
            return SlowQueryReport(
                available=False,
                enabled=False,
                reason=f"{type(exc).__name__}: {exc}",
            )

        if not available:
            return SlowQueryReport(
                available=False,
                enabled=False,
                reason="pg_stat_statements is not available on this server.",
                how_to_enable=how_to_enable,
            )

        if not installed:
            return SlowQueryReport(
                available=True,
                enabled=False,
                reason=(
                    "pg_stat_statements is available but not installed in this "
                    "database, so no statement statistics are being collected."
                ),
                how_to_enable=how_to_enable,
            )

        # max_exec_time and the total_exec_time column name both arrived in
        # PG13. Falling back keeps this working on an older server rather than
        # showing an error where numbers should be.
        for total_column, max_column in (
            ("total_exec_time", "max_exec_time"),
            ("total_time", "NULL"),
        ):
            try:
                rows = (
                    await self.db.execute(
                        text(
                            f"""
                            SELECT query, calls, {total_column}, mean_exec_time,
                                   {max_column}, rows
                              FROM pg_stat_statements
                             WHERE dbid = (
                                       SELECT oid FROM pg_database
                                        WHERE datname = current_database()
                                   )
                          ORDER BY {total_column} DESC
                             LIMIT :limit
                            """
                        ),
                        {"limit": limit},
                    )
                ).all()
                break
            except Exception:
                await self.db.rollback()
                rows = None

        if rows is None:
            return SlowQueryReport(
                available=True,
                enabled=True,
                reason="pg_stat_statements is installed but could not be read.",
            )

        reset = None
        try:
            reset = (
                await self.db.execute(
                    text("SELECT stats_reset FROM pg_stat_statements_info")
                )
            ).scalar_one_or_none()
        except Exception:
            # pg_stat_statements_info only exists from PG14.
            await self.db.rollback()

        return SlowQueryReport(
            available=True,
            enabled=True,
            stats_reset=reset,
            queries=[
                SlowQuery(
                    query=(row[0] or "")[:QUERY_PREVIEW],
                    calls=int(row[1] or 0),
                    total_ms=round(float(row[2] or 0), 3),
                    mean_ms=round(float(row[3] or 0), 3),
                    max_ms=round(float(row[4]), 3) if row[4] is not None else None,
                    rows=int(row[5] or 0),
                )
                for row in rows
            ],
        )

    # ------------------------------------------------------------------
    # Backups
    # ------------------------------------------------------------------

    async def backups(self) -> BackupStatus:
        """
        What this database can see of its own protection.

        Only WAL archiving is visible from inside Postgres. An external
        pg_dump on a cron somewhere is real and this cannot see it, so a
        negative here says "nothing this database knows about" rather than
        "no backups exist" -- overstating it would be worse than saying
        nothing.
        """
        try:
            archive_mode = (
                await self.db.execute(text("SHOW archive_mode"))
            ).scalar_one()
            archive_command = (
                await self.db.execute(text("SHOW archive_command"))
            ).scalar_one()
            row = (
                await self.db.execute(
                    text(
                        "SELECT archived_count, last_archived_time, failed_count, "
                        "last_failed_time, stats_reset FROM pg_stat_archiver"
                    )
                )
            ).one()
        except Exception as exc:
            return BackupStatus(
                configured=False,
                summary=f"Could not read archiver state: {type(exc).__name__}: {exc}",
            )

        configured = archive_mode in ("on", "always")
        failed_count = int(row[2] or 0)

        if not configured:
            summary = (
                "WAL archiving is off, so this database has no point-in-time "
                "recovery. Anything backing it up is external and invisible "
                "from here."
            )
        elif failed_count and row[3] is not None and (
            row[1] is None or row[3] > row[1]
        ):
            summary = (
                f"WAL archiving is on but the most recent attempt failed "
                f"({failed_count} failures total)."
            )
        else:
            summary = "WAL archiving is on and the last attempt succeeded."

        return BackupStatus(
            configured=configured,
            summary=summary,
            archive_mode=archive_mode,
            archive_command=archive_command or None,
            archived_count=int(row[0] or 0),
            last_archived_at=row[1],
            failed_count=failed_count,
            last_failed_at=row[3],
            stats_reset=row[4],
            healthy=(
                None
                if not configured
                else not (row[3] is not None and (row[1] is None or row[3] > row[1]))
            ),
        )
