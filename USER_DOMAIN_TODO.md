# User domain — everything needed

Actor refactor + the Manage-Users surface the admin frontend needs.

Files in play: `app/domains/user/{service,admin_service,repository,schemas,storage,redis}.py`,
`app/api/users.py`, `app/auth/router.py`, one migration.

---

## 0. Facts that shape the work

- **There is no user listing.** `list_users(limit, offset)` exists on the
  repository but no service or route calls it. The only listing today is
  `GET /colleges/user_items`, hardcoded to the caller's own college, cursor
  only, no filters, no total.
- **`users` has no `is_active` and no `updated_at`.** Both need adding.
- **Hard delete is not currently possible.** 17 tables carry a
  `users.id` foreign key and all but `posts.reviewed_by` are `nullable=False`.
  Only 5 relationships (`interests`, `open_to`, `reactions`, `comments`,
  `badges`) declare an ORM cascade. `posts`, `chat_*`, `collaboration_requests`,
  `notifications`, `activity`, `moderation_logs.coach_id` and `probabilities`
  have none, so `DELETE FROM users` raises an IntegrityError. See the decision
  below.
- `UserService.add_user(actor, payload)` already takes an `actor` and already
  uses `require_college_permission` + `require_assignable_role`. It is the
  template the rest of this follows.
- `UserStorage.get_author` returns `None` on a cache miss instead of falling
  back to the DB (`# TODO` in place). Any admin listing must read the
  repository, not the cache.
- Every user write must invalidate `UserRedisStore` (which drops both the
  user key and the profile key) **and** reindex the search document.
- `User` schema deliberately never exposes `email`. An admin table needs it,
  so that needs a separate staff-only schema rather than a change to `User`.

---

## 1. `app/rules` — no changes expected

`CREATE_USER` is already college-scoped. Two new permissions are needed:

- [x] `Permission.MANAGE_USER` — edit / deactivate / reset. `STAFF_ROLES`,
      college-scoped.
- [x] `Permission.DELETE_USER` — `PLATFORM_ROLES` only.
- [x] Add both to `PERMISSIONS`; add `MANAGE_USER` to `COLLEGE_SCOPED`
      (`DELETE_USER` is admin-only so scoping is moot).

---

## 2. Migration

- [x] `users.is_active boolean not null default true`
- [x] `users.updated_at timestamptz`
- [x] `users(college_id, role)` — the listing's main filter.
- [x] `users(email)` already unique-indexed. `users(username)` is **not**
      indexed and `q` will search it.
- [x] Backfill `updated_at = created_at` for existing rows.

---

## 3. `service.py` — actor-aware common layer

- [x] `update_profile(actor, profile)` — self only, drop the `user_id` param
      so a caller cannot pass someone else's id.
- [x] `get_user` / `get_profile` unchanged; these are public reads.
- [x] `add_user(actor, payload)` — switch to `actor.require(...)`.

## 4. `admin_service.py` — new file, staff layer

- [x] `list_users(actor, filters, limit, offset)` — `actor.scope_college`
      forces a moderator to their own campus.
- [x] `update_user(actor, user_id, payload)` — role / college / is_alumni.
- [x] `set_active(actor, user_id, is_active)`.
- [x] `delete_user(actor, user_id)` — admin only.
- [x] `reset_password(actor, user_id)` — admin only, returns a temp password.
- [x] `bulk_action(actor, user_ids, action, value)`.
- [x] `permissions_for(actor)` — backs `GET /users/me/permissions`.
- [x] **Guards that must exist on every write:**
      - a moderator may not act on staff (`role in STAFF_ROLES`)
      - nobody may deactivate or delete **themselves**
      - a moderator may not move someone to another college
      - `require_assignable_role` on any role change

## 5. `repository.py`

- [x] `list_users(...)` — rewrite with `college_id`, `role`, `is_alumni`,
      `is_active`, `q` (ILIKE username/email), `sort`, `order`, `limit`,
      `offset`. Reuse the escaping helper from the post repository.
- [x] `update_fields(user_id, changes)` — partial column update.
- [x] `set_active_bulk(user_ids, is_active)`.
- [x] `set_password(user_id, hashed)`.
- [x] `_flat_select` gains `is_active` so the search document can carry it.

## 6. `schemas.py`

- [x] `UserAdminRow` — `UserBasic` + `email`, `is_active`, `created_at`,
      `updated_at`. Staff-only; the public `User` keeps hiding email.
- [x] `UserUpdate {role?, college_id?, is_alumni?}` — all optional.
- [x] `UserListFilters` — a `Depends()`-able query model (**not**
      `Annotated[..., Query()]`; that form stops flattening when another
      query param sits beside it).
- [x] `BulkUserAction {user_ids, action, value}` + result shape mirroring
      `BulkModerationResult`.
- [x] `TempPasswordPayload {user_id, temp_password}`.
- [x] `MyPermissions {role, permissions, college_id, is_platform_wide}`.

## 7. `app/api/users.py`

- [x] `GET /users/me/permissions` — **build first**, unblocks the frontend.
- [x] `GET /users` → `Page[UserAdminRow]`, staff only.
- [x] `PATCH /users/{user_id}`
- [x] `POST /users/{user_id}/deactivate` · `/activate`
- [x] `POST /users/{user_id}/reset_password`
- [x] `POST /users/bulk`
- [x] `DELETE /users/{user_id}`
- [x] Route order: every literal path (`/me/permissions`, `/bulk`) must be
      declared **before** `/{user_id}`.

## 8. `app/auth/router.py`

- [x] Block login for a deactivated account — otherwise "deactivate" does
      nothing at all. 403 with a distinct code, not the invalid-credentials
      401, so the frontend can say why.

## 9. Verify — DONE, all green against the live stack

- [x] Moderator lists only own-college users whatever `college_id` is passed.
- [x] Moderator cannot edit, deactivate or delete a staff account.
- [x] Moderator cannot move a user to another college.
- [x] Nobody can deactivate or delete themselves.
- [x] Non-staff gets 403 on every route here; anonymous 401.
- [x] Deactivated user cannot log in.
- [x] Every write invalidates both cache keys and reindexes the user.
- [x] `email` never appears in a non-staff response.


---

## Decisions — settled

- **Delete** refuses with 409 + content counts as soon as the person has
  written anything; admin only. Deactivation is the answer for anyone with a
  history.
- **Deactivation hides content.** Handled by making `compute_is_active` take
  `author_is_active`, so the pools, the search index and `_is_visible_to` all
  follow the one derivation they already shared. No parallel visibility rule.
- **`GET /users` is staff only** and carries email, via its own
  `UserAdminRow`. The public `User` schema still never exposes an email.
- All three moderator limits enforced in `_check_can_manage` / `_refuse_self`.

## Follow-ups noted, not done here

- `UserStorage.get_author` still returns `None` on a cache miss instead of
  falling back to the database (pre-existing `# TODO`).
- Reactivating a user re-runs the visibility sweep over every post they have
  ever written. Fine at current scale; needs batching if someone has
  thousands.
- The temporary password is returned in the response body because there is no
  mail delivery. It will appear in any client-side request log.
- `Page.total` is the page size here too, so the user table paginates by
  "load until short page" until a real count is added.

Verified end to end by the suites in `tests/`. Both migrations are applied.
