# College domain — everything needed

Actor refactor + the Manage-Colleges surface and the campus pages the feed
needs. Follows the pattern already set by the post and user domains.

Files in play: `app/domains/colleges/{service,admin_service,repository,schemas,storage,redis}.py`,
`app/domains/colleges/pools/{post_pool,user_pool}.py`, `app/api/colleges.py`.
No migration expected.

---

## 0. Facts that shape the work

- **This domain has not been actor-refactored yet.** `add_college` and
  `edit_college` still take a raw `User` as `actor` and call the module-level
  `require_permission` / `require_college_permission`. Everything else here
  has no permission check at all.
- **`GET /colleges` dumps every college unpaginated**, ordered by name, with
  no counts and no search. The repository docstring says this is deliberate
  ("a bounded reference table a client renders whole") — that reasoning holds
  for a signup picker but not for the admin table, which needs counts and
  paging. Expect to keep the cheap list and add a separate admin listing
  rather than break the signup path.
- **There is no delete.** Create and edit exist; nothing removes a college.
- **`/colleges/user_items` is hardcoded to the caller's own college** — the
  admin needs it per campus.
- **`CollegeRepository.get_users` does not filter `is_active`.** Since
  deactivated users are now hidden from search and their posts pulled from
  the feed, the campus people list is the one place they still show up.
  **Fix this in the same pass** — see 3.
- `get_college` is cached per id (`college:{id}`, 8h) and invalidated on
  edit. There is no cached whole-list, so a new college appears immediately.
- `CollegeBasic` is `app/schemas/common.College`, shared by post and user
  responses. Adding counts to it would widen every payload that embeds a
  college — the admin row needs its own schema.
- `colleges.id` is referenced by `users.college_id` (not null),
  `posts.college_id` (not null) and `posts.restricted_to_college_id`
  (nullable). Delete has the same shape as the user one: refuse while
  anything points at it.

---

## 1. `app/rules`

- [x] `Permission.DELETE_COLLEGE` — `PLATFORM_ROLES` only.
- [x] `Permission.VIEW_COLLEGE_STATS` — `STAFF_ROLES`, college-scoped.
- [x] `CREATE_COLLEGE` / `EDIT_COLLEGE` already exist and `EDIT_COLLEGE` is
      already in `COLLEGE_SCOPED`. No change.

## 2. `service.py` — actor-aware common layer

- [x] `add_college(actor, payload)` → `actor.require(Permission.CREATE_COLLEGE)`.
- [x] `edit_college(actor, college_id, payload)` →
      `actor.require(Permission.EDIT_COLLEGE, college_id)`.
- [x] Drop the `require_permission` / `require_college_permission` imports
      once both are switched.
- [x] `get_college` / `get_colleges` stay public and unauthenticated — the
      signup flow reads them before there is a user.
- [x] `get_user_pool_members(college_id, ...)` — take a `college_id`
      parameter rather than having the route pass `current_user.college_id`,
      so one method serves both "my college" and "any college".

## 3. `repository.py`

- [x] **`get_users` must filter `is_active = true`.** Deactivated accounts
      are out of search and their posts are out of the feed; leaving them in
      the campus people list is the last hole. This also means the user pool
      must be rebuilt when someone is deactivated — see 7.
- [x] `get_users` gains `role`, `is_alumni`, `q` for the People tab.
- [x] `list_colleges(q, sort, order, limit, offset)` for the admin table —
      leave `get_colleges()` alone for the signup picker.
- [x] `counts_for(college_id)` → users, posts, pending, active-this-week, in
      one grouped query rather than four round trips.
- [x] `counts_for_all()` → the same per college, for the admin table and for
      `GET /admin/stats/colleges`. One query with `GROUP BY college_id`, not
      N+1 over the listing.
- [x] `references(college_id)` → `{users, posts, restricted_posts}` so delete
      can refuse with the counts, the way the user delete does.
- [x] `delete(college_id)`.

## 4. `admin_service.py` — new file

- [x] `list_colleges(actor, filters, limit, offset)` — admin sees all; a
      moderator or coach sees only their own (a one-row table, but the route
      should not 403 them out of the screen entirely — confirm which).
- [x] `college_stats(actor, college_id)` — `actor.require(VIEW_COLLEGE_STATS,
      college_id)`.
- [x] `delete_college(actor, college_id)` — admin only, refuse with 409 +
      counts while any user or post references it. **Put the counts under
      `detail["payload"]`** — the error handler drops any other key.
- [x] `list_staff(actor, college_id)` — the `UserAdminService.list_users`
      filter with `role in STAFF_ROLES`. Reuse it rather than a second query.
- [x] Invalidate the college cache and reindex on every write; on delete,
      also `delete_college_search`.

## 5. `schemas.py`

- [x] `CollegeAdminRow` — `CollegeBasic` + `user_count`, `post_count`,
      `pending_count`. Do **not** add these to the shared `CollegeBasic`.
- [x] `CollegeStats {users, posts, pending, active_this_week}`.
- [x] `CollegeListFilters` — `Depends()`-able, **not**
      `Annotated[..., Query()]` (that form stops flattening when another
      query param sits beside it).
- [x] `CollegePeopleFilters {role, is_alumni, q}`.

## 6. `app/api/colleges.py`

- [x] `GET /colleges` — leave as the public unpaginated picker.
- [x] `GET /colleges/admin` → `Page[CollegeAdminRow]` with `q`, sort, paging
      and inline counts. *(Or make it `GET /colleges?paginated=true`;
      a separate path is cleaner and cannot break the signup call.)*
- [x] `GET /colleges/{college_id}/stats`
- [x] `DELETE /colleges/{college_id}`
- [x] `GET /colleges/{college_id}/staff`
- [x] `GET /colleges/{college_id}/users` — the campus People tab, with
      `role`, `is_alumni`, `q`, cursor. This is what the frontend's
      `/student/alumni → colleges` redirect is waiting on.
- [x] Keep `/colleges/user_items` as the "my college" shorthand, or retire it
      in favour of the above — decide.
- [x] Route order: `/admin`, `/my_college`, `/post_items`, `/user_items` are
      all literals and must stay **before** `/{college_id}`.
- [x] Switch `add_college` / `edit_college` routes to `Depends(get_actor)`.

## 7. Pools and cache

- [x] `CollegeUserPool` is built from `get_users`, so once that filters
      `is_active` the pool must be rebuilt when someone is deactivated.
      `UserAdminService._resync_authored_posts` is the natural place to also
      drop `college:users:{college_id}`.
- [x] Deleting a college must clear `college:{id}`,
      `college:users:{id}` and `college:posts:{id}`.
- [x] Renaming a college does not touch the post/user documents that embed
      its name — confirm nothing caches the name outside `college:{id}`.
      **Resolved.** `post:{id}` used to be written with the college joined
      into it, so a rename kept serving the old name for the whole 8h post
      TTL. The post cache now stores the post's own row only and the college
      is hydrated per-read from `college:{id}`, which the edit already busts.
      Same for the category and the author. Pinned by
      `tests/verify_entity_hydration.py`.

## 8. Verify — DONE, all green against the live stack

- [x] Moderator can edit only their own college; admin any.
- [x] Non-staff 403 on create / edit / delete / stats; anonymous 401.
- [x] `GET /colleges` still works unauthenticated (signup path).
- [x] Delete refused with 409 + counts while users or posts reference it.
- [x] Delete succeeds for an empty college and clears cache + search doc.
- [x] Counts on the admin row match the per-college stats endpoint.
- [x] A deactivated user disappears from `/colleges/{id}/users`.
- [x] Editing a college busts `college:{id}` and reindexes it.

---

## Decisions — settled

1. **`GET /colleges` untouched** — still the public, unpaginated,
   unauthenticated picker the signup flow reads. The admin table is a
   separate `GET /colleges/admin`.
2. **A moderator gets the college table**, returning the single row for their
   own campus rather than a 403, so the screen still loads.
3. **`/colleges/user_items` kept** as the "my college" shorthand, now built on
   the same per-college method.
4. **`GET /colleges/{id}/users` is open to any signed-in user, any campus** —
   matching how public posts already read cross-college.

## Follow-ups noted, not done here

- `list_staff` reads up to 200 members and filters in Python. Fine for a
  campus roster; give it a real `role IN (...)` query if a college ever gets
  big enough for that to matter.
- `active_this_week` counts people who posted. It undercounts readers until
  there is a last-seen signal (Phase 2 in ADMIN_API_PLAN.md).
- `GET /colleges/{id}/users` returns a plain list capped at `limit`, not a
  cursor page. The cursor version is `/colleges/user_items` and the pooled
  `/{id}/post_items`; add a cursor here if the People tab needs to scroll.
- `Page.total` is the page size here too, same as the other tables.

Verified by `tests/verify_post_user_domains.py` (220 checks, 34 of them
college), `tests/verify_search_and_cache.py` (15 checks) and
`tests/verify_entity_hydration.py` (45 checks).
