"""
Staff operations on other people's accounts.

Composes UserService for the reads it shares, and owns everything that needs
a permission check: listing the user table, editing an account, taking one
out of service, and deleting one.

Three guards run on every write here, and they are the reason this is a
separate service rather than a flag on the public one:

  * a moderator may not touch a staff account
  * a moderator may not move someone to another college
  * nobody may deactivate or delete themselves
"""
import secrets
from uuid import UUID

from fastapi import HTTPException

from app.auth.security import get_password_hash
from app.domains.user.repository import UserRepository
from app.domains.user.schemas import (
    BulkUserActionType,
    BulkUserFailure,
    BulkUserResult,
    MyPermissions,
    UserAdminRow,
)
from app.domains.user.service import UserService
from app.domains.user.storage import UserStorage
from app.rules import Actor, Permission, is_staff

# Length of a generated temporary password, in bytes of entropy.
TEMP_PASSWORD_BYTES = 9


def _forbidden(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=403, detail={"code": code, "message": message})


class UserAdminService:

    def __init__(self, db):
        self.db = db
        self.user_repo = UserRepository(db)
        self.user_store = UserStorage(db, user_repo=self.user_repo)
        self.user_svc = UserService(db)

    # ------------------------------------------------------------------
    # Shared plumbing
    # ------------------------------------------------------------------

    def _search(self):
        from app.domains.search.service import SearchService

        return SearchService(self.db)

    async def _invalidate(self, user_id: UUID) -> None:
        """
        Drop both cached copies and bring the search document in line.

        Every write in this service ends here: a stale cache would keep
        showing a deactivated account as live.
        """
        await self.user_store.user_redis_store.delete(user_id)
        await self._search().update_user_search(user_id)

    async def _require_target(self, user_id: UUID):
        user = await self.user_repo.get_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=404,
                detail={"code": "user_not_found", "message": "User not found"},
            )

        return user

    def _check_can_manage(self, actor: Actor, target) -> None:
        """
        The three guards, in one place.

        Called before every write. The permission check itself already
        confirmed the caller is staff acting within their own college; this
        adds who they may point that authority at.
        """
        actor.require(Permission.MANAGE_USER, target.college_id)

        # A moderator manages members, not colleagues. Only an admin changes
        # another staff account.
        if is_staff(target.role) and not actor.is_platform_wide:
            raise _forbidden(
                "staff_account",
                "Only an admin can manage a staff account",
            )

    @staticmethod
    def _refuse_self(actor: Actor, user_id: UUID, what: str) -> None:
        """
        Nobody takes their own account out of service, admins included.
        Locking the last admin out of the platform is not a recoverable
        mistake.
        """
        if actor.id == user_id:
            raise _forbidden(
                "cannot_target_self",
                f"You cannot {what} your own account",
            )

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------

    @staticmethod
    def permissions_for(actor: Actor) -> MyPermissions:
        """What the caller may do. Read straight off the rules tables."""
        return MyPermissions(
            user_id=actor.id,
            role=actor.role,
            college_id=actor.college_id,
            is_platform_wide=actor.is_platform_wide,
            permissions=sorted(p.value for p in actor.permissions),
        )

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def list_users(
        self,
        actor: Actor,
        filters,
        limit: int = 20,
        offset: int = 0,
    ) -> list[UserAdminRow]:
        """
        One page of the admin user table.

        Whatever college_id the caller sent, scope_college decides what the
        query actually filters on -- a moderator gets their own campus, and a
        403 if they ask for another.
        """
        college_id = actor.scope_college(filters.college_id)

        actor.require(Permission.MANAGE_USER, college_id)

        users = await self.user_repo.list_users(
            limit=limit,
            offset=offset,
            college_id=college_id,
            role=filters.role,
            is_alumni=filters.is_alumni,
            is_active=filters.is_active,
            q=filters.q,
            sort=filters.sort.value,
            order=filters.order.value,
        )
        return [UserAdminRow.model_validate(u) for u in users]

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def update_user(self, actor: Actor, user_id: UUID, payload) -> UUID:
        """Change someone's role, college or alumni flag."""
        target = await self._require_target(user_id)

        self._check_can_manage(actor, target)

        changes = payload.model_dump(exclude_unset=True)

        if not changes:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "nothing_to_update",
                    "message": "No fields were given to change",
                },
            )

        new_role = changes.get("role")

        if new_role is not None and new_role != target.role:
            # A moderator can only hand out the roles app/rules lets them.
            actor.require_assignable_role(new_role)

        new_college = changes.get("college_id")

        if new_college is not None and new_college != target.college_id:
            # Moving someone to another college moves them out of a
            # moderator's reach, so only a platform role may do it.
            if not actor.is_platform_wide:
                raise _forbidden(
                    "cannot_move_college",
                    "Only an admin can move someone to another college",
                )

            if not await self.user_repo.college_exists(new_college):
                raise HTTPException(
                    status_code=422,
                    detail={
                        "code": "college_not_found",
                        "message": "That college does not exist",
                    },
                )

        await self.user_repo.update_fields(user_id, changes)
        await self._invalidate(user_id)

        return user_id

    async def set_active(
        self,
        actor: Actor,
        user_id: UUID,
        is_active: bool,
    ) -> UUID:
        """
        Take an account out of service, or bring it back.

        Deactivating also hides everything the person wrote: their posts are
        recomputed through the same is_active derivation the rest of the app
        uses, which drops them from the pools and the search index. Bringing
        the account back restores whatever was publicly visible before --
        a post that was held or archived stays hidden, because its own state
        still says so.
        """
        target = await self._require_target(user_id)

        # Self first: it is the most specific reason and it applies to every
        # role, so checking it after the staff guard would tell a moderator
        # their own account is "a staff account" rather than their own.
        self._refuse_self(actor, user_id, "deactivate")
        self._check_can_manage(actor, target)

        if target.is_active == is_active:
            return user_id

        await self.user_repo.set_active(user_id, is_active)
        await self._invalidate(user_id)

        await self._resync_authored_posts(user_id, is_active)
        await self._clear_college_user_pool(target.college_id)

        return user_id

    @staticmethod
    async def _clear_college_user_pool(college_id) -> None:
        """
        Drop the campus's people pool.

        The pool is built from a query that now excludes deactivated
        accounts, so it has to be rebuilt after someone is taken out of
        service or brought back -- otherwise the People tab keeps serving the
        ranking it cached beforehand.
        """
        if college_id is None:
            return

        from app.redis.client import get_redis
        from app.redis.keys import RedisKeys

        try:
            await get_redis().delete(RedisKeys.pool(f"college:users:{college_id}"))
        except Exception:
            # A stale pool is a wrong listing, not a failed deactivation.
            pass

    async def _resync_authored_posts(
        self,
        user_id: UUID,
        author_is_active: bool,
    ) -> list[UUID]:
        """
        Recompute visibility across everything this person wrote, then
        reindex and bust the cache for the posts that actually changed.
        """
        from app.domains.post.storage import PostStorage

        post_store = PostStorage(self.db)

        changed = await post_store.post_repo.set_author_posts_visibility(
            user_id=user_id,
            author_is_active=author_is_active,
        )

        for post_id in changed:
            await post_store.redis_store.delete(str(post_id))
            await self._search().update_post_search(post_id)

        return changed

    async def reset_password(self, actor: Actor, user_id: UUID) -> str:
        """
        Issue a temporary password and return it once.

        Admin only. There is no mail delivery yet, so the caller reads it off
        the response and passes it on; it is hashed before storage like any
        other password and is never readable again.
        """
        target = await self._require_target(user_id)

        actor.require(Permission.RESET_PASSWORD, target.college_id)

        temp_password = secrets.token_urlsafe(TEMP_PASSWORD_BYTES)

        await self.user_repo.set_password(user_id, get_password_hash(temp_password))
        await self.user_store.user_redis_store.delete(user_id)

        return temp_password

    async def delete_user(self, actor: Actor, user_id: UUID) -> UUID:
        """
        Permanently remove an account. Admin only.

        Refused as soon as the person has written anything. Most of the
        tables pointing at users.id declare no cascade, so the delete would
        fail on a foreign key; more to the point, erasing an author silently
        tears holes in other people's comment threads. Deactivation is the
        answer for anyone with a history.
        """
        target = await self._require_target(user_id)

        self._refuse_self(actor, user_id, "delete")
        actor.require(Permission.DELETE_USER, target.college_id)

        counts = await self.user_repo.content_counts(user_id)

        if any(counts.values()):
            # The counts go under `payload`: the error handler passes only
            # code, message and payload through, so anything else set here
            # would never reach the client.
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "user_has_content",
                    "message": (
                        "This account has content and cannot be deleted. "
                        "Deactivate it instead."
                    ),
                    "payload": counts,
                },
            )

        await self.db.delete(target)
        await self.db.commit()

        await self.user_store.user_redis_store.delete(user_id)
        await self._search().delete_user_search(user_id)

        return user_id

    async def bulk_action(
        self,
        actor: Actor,
        user_ids: list[UUID],
        action: BulkUserActionType,
        value=None,
    ) -> BulkUserResult:
        """
        Apply one action to a selection.

        Every id is checked on its own, so a selection that happens to
        include a colleague or the caller themselves updates the rest and
        reports what it refused.
        """
        result = BulkUserResult()

        found = await self.user_repo.users_by_ids(user_ids)
        by_id = {user.id: user for user in found}

        allowed = []

        for user_id in user_ids:
            target = by_id.get(user_id)

            if target is None:
                result.failed.append(
                    BulkUserFailure(user_id=user_id, reason="not_found")
                )
                continue

            try:
                if action is not BulkUserActionType.assign_role:
                    self._refuse_self(actor, user_id, "deactivate")

                self._check_can_manage(actor, target)

                if action is BulkUserActionType.assign_role:
                    actor.require_assignable_role(value)
            except HTTPException as exc:
                detail = exc.detail
                reason = (
                    detail.get("code", "forbidden")
                    if isinstance(detail, dict)
                    else "forbidden"
                )
                result.failed.append(
                    BulkUserFailure(user_id=user_id, reason=reason)
                )
                continue

            allowed.append(user_id)

        if not allowed:
            return result

        if action is BulkUserActionType.assign_role:
            for user_id in allowed:
                await self.user_repo.update_fields(user_id, {"role": value})
                await self._invalidate(user_id)
            result.updated = allowed
            return result

        is_active = action is BulkUserActionType.activate

        updated = await self.user_repo.set_active_bulk(allowed, is_active)

        for user_id in updated:
            await self._invalidate(user_id)
            await self._resync_authored_posts(user_id, is_active)
            await self._clear_college_user_pool(by_id[user_id].college_id)

        result.updated = updated

        return result
