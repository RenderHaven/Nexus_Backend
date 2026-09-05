# Admin / Staff API — build plan

Scope: the endpoint list required by the frontend admin + moderator + success-coach
rebuild, checked against what the backend actually has today.

## What already exists

| Area | Today |
|---|---|
| Roles & scoping | `app/rules/` — `Permission`, `PERMISSIONS`, `COLLEGE_SCOPED`, `ASSIGNABLE_ROLES`, `require_college_permission`. Complete enough to drive everything below. |
| Moderation | `GET /posts/moderation/{status}` (bare array, no total, no filters, `college_id` is an *optional* param — not forced), `PATCH /posts/{post_id}/moderation` (no reason persisted from the API layer). |
| Moderation audit | `moderation_logs` table + `ModerationLogService` exist and every call site is wired — but `_record` only calls `logger.info`; the DB insert is a `# TODO`. **The table has no rows.** History starts empty and cannot be backfilled. |
| Users | `/users/me`, `POST /users`, `GET /users/{id}`, `/{id}/profile`, `/{id}/post_items`. No list, no filters, no update, no deactivate. |
| Colleges | `GET /colleges` (dumps all, unpaginated, no counts), `POST`, `PATCH /{id}`, `GET /{id}`, `/user_items` (hardcoded to caller's college), `/{id}/post_items`. No delete, no stats, no per-college user list. |
| Home | `/home/trending_topics`, `/home/news`, `/home/banners` — all hardcoded sample data in `HomeService`. No tables. |
| Search | OpenSearch. `post_document` indexes only visible posts; a pending/held/removed post is **deleted from the index**. Query always filters `is_active: true`. Staff cannot find a pending post through `/search` by construction. |

### Schema gaps that gate work
- `users`: no `is_active`, no `updated_at`. Deactivate/activate needs a migration.
- No `reports` table — no reporting mechanism of any kind exists.
- No `news` / `banners` tables — those endpoints are stubs.
- No generic `activity_log` — `moderation_logs` covers post decisions only, not role changes or college edits.
- `colleges` has no denormalised `user_count` / `post_count` — counts must be aggregated per request (fine at current scale).

---

## Service architecture (decided)

**Actor + composition.** The role is an *argument*, never a subclass. Rejected a
`Student -> Moderator -> Admin` inheritance chain because roles are a matrix in
`app/rules/permissions.py`, not a ladder (`moderator` and `success_coach` are
peers, as are `student`/`alumni`/`guest`), and because the real difference
between a moderator and a student is query *scope*, not method count.

Per domain:

```
app/domains/<domain>/
  repository.py     # SQL. services may use directly.
  storage.py        # cache + repo. services may use directly.
  service.py        # domain logic, actor-aware. the shared/common layer.
  admin_service.py  # staff-only writes; COMPOSES service.py (only where needed)
```

`app/rules/actor.py` -- `Actor` is the one `_verify_user`. Built once per request
by `get_actor` / `get_actor_optional` in `app/auth/deps.py`.

```python
actor.require(perm, college_id)   # 401 anon / 403 wrong role / 403 wrong college
actor.scope_college(requested)    # admin -> requested|None, staff -> forced own
actor.can_see_hidden(college_id)  # staff read hidden rows, own campus only
actor.permissions                 # backs GET /users/me/permissions
```

`scope_college` is what enforces "a moderator sees only his college": it discards
the `college_id` off the query string and substitutes the caller's own, so a
listing endpoint cannot leak another campus even if the route forgets to check.

**Rollout order:** `post` -> `user` -> `colleges` -> `search`, then the rest
incrementally. The remaining eleven domains keep working untouched -- `Actor` is
additive and the old `require_*` helpers still exist.

**Status:** `app/rules/actor.py` + `get_actor` / `get_actor_optional` are done and
verified (admin unrestricted, staff forced to own college, cross-college 403,
anonymous 401, `can_see_hidden` true only for staff).

**Search:** one `search(query, actor)`, no subclass -- the actor sets
`include_hidden` and the forced `college_id` filter on the same query builder.

---

## PHASE 1 — DONE

All of it is built, verified against a live Postgres / Redis / OpenSearch
stack, and covered by `tests/verify_post_user_domains.py` (220 checks) and
`tests/verify_search_and_cache.py` (15 checks). Both migrations are applied.

Four domains were refactored onto `Actor` along the way -- post, user,
colleges -- and a new `stats` domain added for the dashboard.

### 1.1 Foundations (do first — everything else leans on these)
- [x] `GET /users/me/permissions` → `{role, permissions: [...], college_ids: [...], is_platform_wide}`. Now a straight serialisation of `Actor`. Kills the frontend's role-guessing hack in the layout.
- [x] `Actor` in `app/rules/actor.py` with `require` / `scope_college` / `can_see_hidden` / `permissions`, plus `get_actor` and `get_actor_optional` in `app/auth/deps.py`. Every list endpoint below takes an `Actor`.
- [x] `app/api/admin.py` mounted at `/admin`, backed by a new `app/domains/stats/` (schemas + repository + service).
- [x] Standardise a `Page[T] = {items, total, limit, offset}` schema in `app/schemas/common.py` alongside the existing `Paginated` cursor type.

### 1.2 Moderation queue (B)
- [x] `GET /posts/moderation/counts?college_id=` — one grouped count query, feeds the tab badges.
- [x] Extend `GET /posts/moderation/{status}`: `user_id`, `category_id`, `type`, `q`, `date_from`, `date_to`, `sort=created_at|reviewed_at|engagement`, `order`, and **return `{items, total}`**. Force `college_id` via 1.1. *Breaking response change — version it or update the contract in the same PR as the frontend.*
- [x] `ModerationUpdate` → add `note: str | None`; pass it through `update_moderation_status` (the service already accepts `note`, the API just drops it).
- [x] **Persist `moderation_logs`.** `ModerationLogService._record` only writes to stdout — the table has never received a row. Fill in the insert first; everything below that reads history depends on it.
- [x] `GET /posts/{post_id}/moderation_history` — readable by the author, own-college staff, or admin.
- [x] `PATCH /posts/moderation/bulk` `{post_ids, moderation_status, note}` — loop the existing service call inside one transaction, return per-id results.
- [x] `GET /admin/activity?limit=&offset=` — chronological `moderation_logs` stream, college-scoped. Offset rather than cursor, to match the other admin tables.

### 1.3 Users (C)
- [x] Migration: `users.is_active boolean not null default true`, `users.updated_at`.
- [x] `GET /users?college_id=&role=&is_alumni=&is_active=&q=&sort=&order=&limit=&offset=` → `{items, total}`, college forced for non-admin. Replaces the unusable `/colleges/user_items` for table use.
- [x] `PATCH /users/{user_id}` — role / college / is_alumni. Reuse `require_assignable_role`; moderator restricted to own-college non-staff.
- [x] `POST /users/{user_id}/deactivate` · `/activate`.
- [x] `DELETE /users/{user_id}` — admin only. Check FK cascades on posts/comments/reactions first; likely should refuse when the user has content and steer to deactivate.
- [x] `POST /users/{user_id}/reset_password` — admin only, generates a temp password, returns it once. (Email delivery is Phase 2.)
- [x] `POST /users/bulk` `{user_ids, action, value}` for role-assign / deactivate.
- [x] Every user write must reindex the user document (`SearchService.update_user_search`) and bust the user cache.

### 1.4 Colleges (D)
- [x] Extend `GET /colleges`: `q`, `sort=name|created_at|user_count`, `order`, `limit`, `offset`, `{items, total}`, plus inline `user_count` / `post_count` via a grouped subquery.
- [x] `GET /colleges/{college_id}/stats` — users, posts, pending, active-this-week.
- [x] `DELETE /colleges/{college_id}` — admin only; refuse when users or posts still reference it (FK is `nullable=False` on both).
- [x] `GET /colleges/{college_id}/staff` — filter `GET /users` by `role in STAFF_ROLES`.
- [x] `GET /colleges/{college_id}/users?role=&is_alumni=&q=&cursor=` — generalise the hardcoded `/colleges/user_items`. Backs the campus People tab and the alumni filter the frontend currently redirects away from.

### 1.5 Dashboard stats that are just SQL (A)
These are exact counts / group-bys over existing columns — no modelling required.
- [x] `GET /admin/stats/overview` — users, colleges, posts, pending queue, active-today.
- [x] `GET /admin/stats/posts_timeseries?range=30d&interval=day` — `date_trunc` on `created_at` / `reviewed_at`, split by moderation status.
- [x] `GET /admin/stats/users_timeseries?range=&interval=` — signups per bucket, optional split by role.
- [x] `GET /admin/stats/moderation?range=&college_id=` — counts per status and median `reviewed_at - created_at` work off `posts` today. "Decisions per moderator" needs `moderation_logs` persistence, so it only has data from that point forward.
- [x] `GET /admin/stats/post_breakdown?group_by=type|category|college`.
- [x] `GET /admin/stats/colleges` — per-college rollup; doubles as the Manage-Colleges table source (share the query with 1.4).
- [x] `GET /admin/stats/top_posts?metric=likes|comments|engagement&range=` — orders by existing `like_count` / `comment_count` / `engagement_score`.
- [x] `GET /admin/stats/top_users?metric=posts|xp` — `total_xp` and a post-count aggregate.
- [x] Add covering indexes as these land: `posts(college_id, moderation_status, created_at)`, `posts(reviewed_at)`, `users(college_id, role)`, `moderation_logs(created_at)`, `moderation_logs(coach_id)`.

### 1.6 Staff search (F) — DB-backed for now
- [x] `GET /admin/search?q=&scope=posts|users|colleges|pending&college_id=` backed by **Postgres ILIKE**, reusing the 1.2/1.3 filter layer. OpenSearch cannot serve this — non-approved posts are removed from the index.

---

## PHASE 2 — later (needs new tables, new logic, or a ranking model)

### 2.1 Reporting & audit
- [ ] `reports` table (post_id, reporter_id, reason, status, resolved_by, resolved_at) + `POST /posts/{post_id}/report`, `GET /reports?status=&college_id=`, `PATCH /reports/{id}`. Whole feature is new — nothing exists.
- [ ] Rate limiting / dedupe on reporting, and author notification on removal with the Phase-1 reason.
- [ ] Generic activity log covering role changes, college edits and user deactivation, then widen `GET /admin/activity` beyond post decisions. **Note:** an `activity_log` table already exists in the models (`app/db/models/activity.py`) with `action_type` / `entity_type` / `xp_awarded` — it has never been written to and has zero rows, so it is a starting point, not a working feature.
- [ ] Reversible decisions (un-remove / restore) once history is visible.

### 2.2 Home content management
- [ ] `news` and `banners` tables + `POST/PATCH/DELETE /home/news` and `/home/banners`, college-scoped, with schedule windows (`publish_at`, `expires_at`) and active flags. `HomeService` currently returns fixed samples.

### 2.3 Real analytics
- [ ] `GET /admin/stats/top_posts?metric=engagement` with a *time-decayed* score rather than the raw stored `engagement_score`.
- [ ] Real trending topics — post volume per category over a rolling window weighted by engagement. Replaces the hardcoded `/home/trending_topics`.
- [ ] "Active today / this week" needs a real signal: a `user_activity` / last-seen table or event stream. Phase 1 approximates it from posts+comments, which undercounts readers.
- [ ] Materialised views or a nightly rollup table once per-request aggregation gets slow, plus Redis caching of the overview counters.

### 2.4 Search, properly
- [ ] Index non-approved posts with `moderation_status` + `is_visible` fields instead of deleting them; add a staff-only `include_hidden=true` on `/search`. Requires a mapping change and full reindex (`app/domains/search/scripts/`).
- [ ] `GET /search/suggest?q=&scope=` typeahead — needs an edge-ngram / completion field in the mapping.
- [ ] Role/college facets on user search.

### 2.5 Feed personalisation
- [ ] `POST/DELETE /colleges/{id}/follow`, `GET /colleges/following` + a `college_follows` table, and feed ranking that actually uses it. Only worth building once the feed is ready to consume it.

### 2.6 Operational
- [ ] Password-reset email delivery (Phase 1 returns a temp password inline).
- [ ] Real soft-delete/anonymisation path for users so `DELETE /users/{id}` isn't a FK minefield.
- [ ] Regenerate `api_contract.md` via `scripts/gen_api_contract.py` at the end of each phase.


---

## What Phase 1 actually shipped

**New domains and services**

| | |
|---|---|
| `app/rules/actor.py` | `Actor` — one `require` / `scope_college` / `can_see_hidden` / `owns` for the whole codebase |
| `app/domains/stats/` | schemas + repository + service behind `/admin` |
| `app/domains/post/admin_service.py` | rewritten: queue, counts, bulk, history |
| `app/domains/user/admin_service.py` | new |
| `app/domains/colleges/admin_service.py` | new |
| `app/domains/logs/repository.py` | new — the audit trail is now persisted |

**Bugs found and fixed while building, that were not on the original list**

1. `MODERATE_POST`, `DELETE_ANY_POST` and `CREATE_RESTRICTED_POST` were not in
   `COLLEGE_SCOPED`, so a college-scoped check on them passed for any campus.
2. `ModerationLogService` never wrote a row — the audit trail was a stdout log.
3. A deactivated user's JWT kept working until expiry.
4. Approving a deactivated author's post made it public again.
5. A full search reindex re-added deactivated users.
6. The 409 content counts were dropped by the error handler, which passes
   only `code` / `message` / `payload`.
7. The staff guard masked the self guard, so a moderator deactivating
   themselves was told it was "a staff account".
8. `CollegeRepository.get_users` did not filter `is_active`, and its Redis
   pool cached the pre-deactivation ranking.

**Gotchas worth remembering**

- `Annotated[Model, Query()]` stops flattening into individual query
  parameters as soon as another query parameter sits beside it. Use
  `Depends()` for filter models.
- Literal route paths must be declared before `/{id}` ones, or FastAPI parses
  the literal as a UUID.
- `Page.total` is the page size, by decision. Real per-status totals come
  from `/posts/moderation/counts`.
