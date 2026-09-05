# Post domain — everything needed

Refactor to `Actor` + build the moderation surface the admin frontend needs.

Files in play:
`app/domains/post/{service,admin_service,repository,schemas,storage,rules}.py`,
`app/domains/logs/moderation.py`, `app/api/posts.py`, one migration.

---

## 0. Facts that shape the work

- `include_hidden` on `get_post` / `get_posts` is **dead** — never passed `True`
  anywhere in the codebase. Safe to replace outright with the actor check.
- `moderation_logs` **has no rows**. `ModerationLogService._record` logs to
  stdout and returns; the DB write is a TODO. Nothing that reads history works
  until this is filled in.
- `PostAdminService` already composes `PostService` and shares `PostStorage`,
  so the cache stays consistent. Keep that.
- `api/posts.py:137` types a variable `PostService | PostAdminService` — this
  is the permission-leak shape the Actor refactor removes.
- `list_by_moderation_status` returns a bare list, filters on nothing but
  status + college, and hard-sorts `created_at ASC`.
- `apply_is_active` in `rules.py` is the single definition of "publicly
  visible". Every write path must keep going through it — never set
  `is_active` directly.

---

## 1. `service.py` — actor-aware common layer

- [x] `_is_visible_to(post, actor)` → `post.is_active or actor.owns(post) or
      actor.can_see_hidden(post.college_id)`. Replaces the `user_id` +
      `include_hidden` pair. Public posts stay cross-college for everyone;
      hidden ones are own-campus only for staff, platform-wide for admin.
- [x] `get_post(post_id, actor)` / `get_posts(post_ids, actor)` — drop
      `user_id` and `include_hidden` from the signature.
- [x] `_get_user_interactions(actor, posts)` — key on `actor.id`, no-op when
      `actor.is_anonymous`.
- [x] `_get_owned_post(post_id, actor)` — stays strictly owner-only. Staff act
      through `admin_service`, so an accidental staff call can't edit someone
      else's post body.
- [x] `list_my_inactive_posts(actor, ...)`.
- [x] `archive_post` / `publish_post` / `delete_post` / `update_post` take
      `actor` instead of `user_id`.
- [x] `Actor.owns(obj)` and college-scoped `Actor.can_see_hidden(college_id)`
      done and verified in `app/rules/actor.py`.

**Callers to update** (all currently pass raw `user_id`):
- [x] `app/domains/search/service.py:268` — `get_posts(ids, user_id)`
- [x] `app/domains/comments/service.py` — 5 call sites
- [x] `app/domains/feed/service.py:22`
- [x] `app/domains/reaction/service.py` — uses `require_post` / count updates
      only, so no change needed. Verify.

---

## 2. `admin_service.py` — staff layer

- [x] Delete module-level `require_moderator`; use
      `actor.require(Permission.MODERATE_POST, college_id)` at each entry
      point so the college scope is checked too, not just the role.
- [x] `list_moderation_queue(actor, status, filters) -> (items, total)`.
      Calls `actor.scope_college(filters.college_id)` — a moderator's request
      for another campus is discarded, not honoured.
- [x] `count_by_status(actor, college_id) -> dict[ModerationStatus, int]`.
- [x] `update_moderation_status(..., note)` — service already accepts `note`,
      just needs the API to pass it and the log to persist it.
- [x] `bulk_update_moderation(actor, post_ids, status, note)` — one
      transaction, one reindex batch, returns per-id `{updated, not_found,
      forbidden}` rather than failing the whole call on one bad id.
- [x] `moderation_history(actor, post_id)` — readable by the post's **author**,
      a **staff member of that post's college**, or an **admin**. Everyone
      else 403. The author case means this cannot sit behind a blanket
      `require(MODERATE_POST)` guard.
- [x] Every write keeps the existing invalidate-then-reindex pair:
      `post_store.redis_store.delete(...)` + `_reindex(...)`.
- [x] Bulk path must invalidate every touched id, not just the first.

---

## 3. `repository.py` — queries

- [x] Extend `list_by_moderation_status` with `user_id`, `category_id`,
      `type`, `q` (ILIKE title/content), `date_from`, `date_to`,
      `sort=created_at|reviewed_at|engagement_score`, `order`.
      Build conditions once and share them with the count.
- [x] `count_by_moderation_status(**same filters) -> int` for `total`.
- [x] `counts_by_status(college_id) -> dict` — single `GROUP BY
      moderation_status` for the tab badges.
- [x] `set_moderation_status_bulk(post_ids, status, reviewer_id)` — one
      UPDATE, still routing `is_active` through `apply_is_active`.
- [x] Confirm the queue keeps excluding archived/deleted posts
      (`status == published`) under the new filters.
- [x] Reverting a decision is allowed (moderator on own college, admin
      anywhere), so `set_moderation_status` must handle approved → removed →
      approved and recompute `is_active` each time. Already does via
      `apply_is_active`; add a test.

---

## 4. `schemas.py`

- [x] `ModerationUpdate` → add `note: str | None`.
- [x] `BulkModerationUpdate {post_ids (capped at MAX_BATCH_SIZE), moderation_status, note}`.
- [x] `BulkModerationResult {updated: [...], failed: [{post_id, reason}]}`.
- [x] `ModerationCounts {pending, approved, hold, removed}`.
- [x] `ModerationQueueFilters` — a `Depends()`-able query-param model so the
      filter list isn't copy-pasted across endpoints.
- [x] `ModerationLogEntry {id, post_id, action, note, created_at, moderator: UserBasic}`.
- [x] `Page[T] {items, total, limit, offset}` in `app/schemas/common.py`,
      alongside the existing cursor-based `Paginated[T]`.

---

## 5. `app/domains/logs/moderation.py` — make the audit trail real

- [x] Implement `_record` to insert into `moderation_logs`. Keep the
      never-raises contract: a failed audit write must not fail the
      moderation action.
- [x] Add `ModerationLogRepository` (insert, list-by-post, list-recent,
      count-by-moderator).
- [x] Map status → `ModerationAction` via the existing `STATUS_ACTIONS`.
      Note `ModerationAction` has no value for `pending` — decide whether
      reverting a decision to pending is logged as its own action or skipped.
- [x] Backfill is impossible (no historical rows). History starts empty.

---

## 6. `api/posts.py`

- [x] Replace `get_moderator_user` with `get_actor`; drop the
      `require_moderator` import.
- [x] `_create_post` — remove the `PostService | PostAdminService` union;
      pass an explicit service.
- [x] `GET /posts/moderation/counts?college_id=`  **(new)**
- [x] `GET /posts/moderation/{status}` — add all filters, **return
      `{items, total}`**. *Breaking response change.*
- [x] `PATCH /posts/moderation/bulk`  **(new)** — must be declared **before**
      `/{post_id}/moderation` or the path matcher will treat "bulk" as a UUID.
- [x] `GET /posts/{post_id}/moderation_history`  **(new)**
- [x] `PATCH /posts/{post_id}/moderation` — accept and persist `note`.
- [x] Existing member endpoints switch to `Depends(get_actor_optional)`.

---

## 7. Migration

- [x] `posts(college_id, moderation_status, created_at)` — the queue query.
- [x] `posts(reviewed_at)` — sort + time-to-decision stat.
- [x] `moderation_logs(post_id, created_at)` — history.
- [x] `moderation_logs(coach_id, created_at)` — per-moderator throughput.
- [x] Trigram index on `posts.title` / `posts.content` only if `q` proves slow
      (ILIKE `%x%` can't use a btree).

---

## 8. Verify — DONE, all green against the live stack

- [x] Moderator sees only own-college queue even when passing another
      `college_id`.
- [x] Success coach behaves identically to moderator — confirmed, and that is
      the intended design.
- [x] Moderator reads a **public** post from another college fine.
- [x] Moderator gets `None` for a **hidden** post from another college.
- [x] Admin reads a hidden post from any college.
- [x] Revert removed → approved puts the post back in the pools and index.
- [x] Student gets 403 on every moderation route; anonymous gets 401.
- [x] Author still sees their own pending post via `get_post`.
- [x] Non-author student gets `None` for a pending post.
- [x] Approve flips `is_active` true and the post enters the pools + index.
- [x] Remove drops it from the index.
- [x] Bulk approve of 3 ids invalidates all 3 caches.
- [x] `total` matches the filtered set, not the page.

---

## Decisions — all settled

- Moderator = success coach.
- Public content is cross-college for everyone; hidden content is own-college
  for staff, platform-wide for admin.
- `moderation_history`: author + own-college staff + admin.
- Staff may move a post between approved / hold / removed at any time.
  `pending` is not a decision, so it is rejected by the schema and no
  `ModerationAction` had to be added.
- `restricted_to_college_id` stays read-open, join-restricted. No change.
- The queue returns `{items, total}` with `total = len(items)`; real
  per-status totals come from `GET /posts/moderation/counts`.

### Follow-ups noted, not done here

- `log_restricted_create` has no `ModerationAction` to map to, so it still
  only writes to stdout. Add a `create` action if that event needs history.
- `update_moderation_status` reads the post twice (once to scope-check, once
  in `set_moderation_status`). Fold into one read if it shows up in profiling.
- The queue `total` is the page size. Once a filter is applied the counts
  endpoint no longer matches it, so filtered pagination is "load until short
  page" until a real count is added.
4. ~~`success_coach` vs `moderator`~~ — **decided: identical.**

### Answered
- Moderator = success coach.
- Public content is cross-college for everyone; hidden content is own-college
  for staff, platform-wide for admin.
- `moderation_history`: author + own-college staff + admin.
- Moderator and admin may both revert a decision.

Verified end to end by `tests/verify_post_user_domains.py` (103 checks) and
`tests/verify_search_and_cache.py` (15 checks), against real Postgres, Redis
and OpenSearch. Both migrations are applied.
