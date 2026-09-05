# Infrastructure monitoring

The staff UI has an Infrastructure section — Cache Engine, Search Engine,
Database. Each screen is backed by a monitoring service that lives **next to
the thing it monitors**, not in `app/domains/`. A domain models something the
product has; this models something the deployment has, and it belongs with the
client it wraps.

| Screen | Service | Routes |
|---|---|---|
| Cache Engine | `app/redis/service.py` | `/infra/cache/*` |
| Search Engine | `app/domains/search/opensearch/service.py` | `/infra/search/*` |
| Database | `app/db/service.py` | `/infra/database/*` |

## The three rules

Every monitoring service follows these. They are what separates a monitoring
screen from an outage amplifier.

1. **Bounded sweeps, never unbounded ones.** No `KEYS`, no unfiltered table
   scan. `RedisMonitorService` walks with `SCAN` in batches, stops at
   `SCAN_CAP`, and sets `truncated: true` when it does — so the number is
   honestly a floor rather than silently wrong. Expensive per-item questions
   (`MEMORY USAGE`, `TTL`) run over a sample, not the whole namespace.
2. **Degrade, never raise.** `health()` returns `reachable: false` with the
   error text; the other reads return empty. A screen that 500s alongside the
   thing it monitors is useless at exactly the moment it is needed. Verified
   directly in `tests/verify_cache_engine.py`.
3. **Read-only unless asked.** One method per service may write. For the cache
   that is `invalidate_*`, gated behind `MANAGE_INFRASTRUCTURE` rather than
   the view permission.

## Permissions — administrators only

`VIEW_INFRASTRUCTURE` and `MANAGE_INFRASTRUCTURE`, both `PLATFORM_ROLES`,
which is `{admin}`. A moderator or success coach is staff for their own campus
and gets 403 here, the same as a student. Neither permission is in
`COLLEGE_SCOPED` — there is one Redis, one cluster and one database, so there
is no per-campus view of them to scope to. This is the first pair of
permissions in the app that are deliberately not college-scoped.

The read guard is declared **on the router**, not on each route:

```python
router = APIRouter(dependencies=[Depends(get_infra_reader)])
```

so a route added to `app/api/infra.py` is guarded whether or not its author
remembers to ask. Write routes add `get_infra_admin` on top; a route can only
tighten what the router already requires, never loosen it.
`tests/verify_infra_monitoring.py` enumerates every `/infra` route **from the
live OpenAPI schema** and asserts 401 anonymous and 403 for all five
non-admin roles — so a new unguarded route fails the suite rather than
shipping open.

## Cache Engine specifics

**`app/redis/namespaces.py`** is the table everything keys off. One row per key
shape: pattern, label, declared TTL, description. Key counts, hit rate, TTL
policy and invalidate-by-namespace are all the same question asked of that one
list. Adding a new cached thing means adding a row; nothing in the service
changes.

Order matters — `classify()` takes the first matching pattern, so
`user:profile:*` must sit above `user:*`. The same trap bites `SCAN MATCH`,
whose globs are looser than the table: `invalidate_namespace("user")` scans
`user:*` and then **re-classifies every key**, so busting users cannot take
`user:profile:*` or `user:*:liked_posts` with it. There is a test for exactly
that.

**`app/redis/metrics.py`** records per-namespace hit/miss counters, because
Redis's own `keyspace_hits`/`keyspace_misses` are server-wide and cannot tell
you *which* cache is missing. A miss on `post:{id}` costs a Postgres round trip
on the feed; a miss on `category:{id}` costs nothing. The entity storages call
`metrics.record(namespace, hits=, misses=)` once per read — one line each, in
`post`, `user`, `comment`, `college` and `category` storage. Recording is best
effort and swallows its own errors: a counter is never worth failing a read
over.

Two shapes are kept: a running total per namespace, and hourly buckets that
expire after 25h (25, not 24, so a full day is always present while the newest
bucket is still filling). The server-wide and per-namespace numbers answer
different questions and deliberately do not reconcile.

**The TTL policy panel** shows the declared TTL next to what the live keys
actually say, and flags the disagreement. A namespace declared with an 8h TTL
whose sampled keys have none means something is writing that key without one —
which is how a cache stops being a cache and becomes a leak. It already flags
one real finding: `cursor:*` is written with no expiry and accumulates.

## Search Engine specifics

Search is the one piece of infrastructure the app is built to survive losing —
`OPENSEARCH_URL` is optional, and indexing swallows its own failures so a
search outage cannot fail a user's write. That makes drift the normal state
rather than an alarm, and this screen the only place anyone would notice it.

**Ingest lag** has no queue to report, because there is no queue: indexing is
inline and best effort. Drift (source rows minus indexed documents) is the only
honest measure. A *negative* drift is the dangerous direction — the index
holding documents the database no longer has, i.e. removed content still
searchable.

**Mappings** compares the live mapping against `opensearch/indexes.py` and
flags any difference. A mapping is schema and cannot be changed in place, so a
drift means a rebuild is owed and search is quietly answering with the old
rules until someone runs one. Only the fields declared in source are compared —
OpenSearch fills in defaults nobody wrote down, and comparing wholesale would
report drift on every index forever.

**Reindex** returns 202 and runs in the background: a full rebuild walks every
row of the source table, well past any HTTP timeout. It calls `rebuild_index`
directly rather than `rebuild_all`, because `rebuild_all` closes the shared
OpenSearch client in its `finally` — correct for a CLI script, and would pull
the client out from under live requests. State lives in `infra:reindex:{name}`
in Redis, and a second trigger while one is running is refused.

## Database specifics

**There is no Alembic.** Migrations are idempotent scripts under `app/scripts/`
and nothing records which have run, so "which revision is applied" has no
answer. `app/db/migrations.py` declares what each script should have left
behind — columns, indexes, or a violations query for a data backfill — and the
service checks that against the live schema. For idempotent scripts that is
strictly better than a ledger: it reports the database as it is, not as some
bookkeeping table claims it was left.

**Row counts are estimates** from the statistics collector, never
`SELECT count(*)` per table — that would be one sequential scan per table per
page view. The last autovacuum time sits next to each count, because that is
what the estimate drifts from.

**pg_stat_statements is not installed** on the dev database. The panel says so,
with the exact steps to enable it, rather than returning an empty list that
reads like "nothing is slow".

**Backups** can only see WAL archiving from inside Postgres. An external
`pg_dump` on a cron is real and invisible from here, so a negative says
"nothing this database knows about" rather than "no backups exist".

## Verified

- `tests/verify_cache_engine.py` — 68 checks: auth on every route, health
  against `DBSIZE`, counters moving on real cold/warm reads, namespace
  classification, the inspector, the neighbour-safety of namespace
  invalidation, and the unreachable-Redis path.
- `tests/verify_infra_monitoring.py` — 80 checks: access control over every
  `/infra` route for all six roles, plus the search and database panels
  end to end, including a real background rebuild of the colleges index and a
  dropped index correctly turning its migration pending.

## Known finding

Ingest lag currently reports **negative drift on all three indexes** — the
index holds more documents than the database has rows. Every orphan sampled is
a test fixture (`zz*` usernames): the verification suites tear their rows down
with `psql`, which bypasses the app's index-delete path, so each run leaves
documents behind. Not a production bug, but it accumulates in the dev cluster,
and either the suites should delete their search documents on teardown or the
rebuild should be run periodically.
