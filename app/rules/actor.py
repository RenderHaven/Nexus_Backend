"""
Who is asking, and what that lets them see.

Every service method that behaves differently for a student, a moderator and
an admin takes an Actor rather than branching on role. The role tables in
permissions.py stay the only place that says who may do what; Actor is the
read-only view of those tables for one request.

The two questions services actually ask:

  actor.require(perm, college_id)   may they do this at all?
  actor.scope_college(requested)    which college's rows may they see?

scope_college is what stops a moderator reading another campus: it ignores
whatever college_id arrived on the query string and substitutes their own.
"""
from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException

from app.db.models import UserRole
from app.rules.permissions import (
    PERMISSIONS,
    Permission,
    require_assignable_role,
    require_college_permission,
    require_permission,
)
from app.rules.roles import is_platform_wide, is_staff


@dataclass(frozen=True)
class Actor:
    """The caller, resolved once per request."""

    user: object | None = None

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def is_anonymous(self) -> bool:
        return self.user is None

    @property
    def id(self) -> UUID | None:
        return getattr(self.user, "id", None)

    @property
    def role(self) -> UserRole | None:
        return getattr(self.user, "role", None)

    @property
    def college_id(self) -> UUID | None:
        return getattr(self.user, "college_id", None)

    @property
    def is_staff(self) -> bool:
        return self.role is not None and is_staff(self.role)

    @property
    def is_platform_wide(self) -> bool:
        """Admin. Not confined to a single college."""
        return self.role is not None and is_platform_wide(self.role)

    @property
    def permissions(self) -> frozenset[Permission]:
        """Every permission this role holds. Drives GET /users/me/permissions."""
        if self.role is None:
            return frozenset()
        return frozenset(
            perm for perm, roles in PERMISSIONS.items() if self.role in roles
        )

    # ------------------------------------------------------------------
    # Guards -- one implementation, called from every service
    # ------------------------------------------------------------------

    def can(self, permission: Permission) -> bool:
        return permission in self.permissions

    def require(self, permission: Permission, college_id: UUID | None = None):
        """
        Raise 403 unless the caller holds the permission -- and, when a
        college is given, unless they may use it against that college.
        """
        self._require_authenticated()

        if college_id is None:
            return require_permission(self.user, permission)

        return require_college_permission(self.user, permission, college_id)

    def require_assignable_role(self, target_role: UserRole):
        self._require_authenticated()
        return require_assignable_role(self.user, target_role)

    def _require_authenticated(self):
        if self.user is None:
            raise HTTPException(
                status_code=401,
                detail={
                    "code": "unauthenticated",
                    "message": "Sign in to do that",
                },
            )
        return self.user

    # ------------------------------------------------------------------
    # Scope -- what the caller may read
    # ------------------------------------------------------------------

    def scope_college(self, requested: UUID | None = None) -> UUID | None:
        """
        The college_id a listing query must filter on.

        Admin  -- whatever they asked for, or None meaning every college.
        Staff  -- their own. Asking for a different one is refused rather
                  than quietly rewritten, so a caller is never shown a page
                  that silently means something other than what they asked
                  for.
        Member -- their own.

        Returning None is "no college filter", so only a platform role can
        ever produce it.
        """
        if self.is_platform_wide:
            return requested

        own = self.college_id

        if requested is not None and own is not None and requested != own:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "forbidden",
                    "message": "You can only do this within your own college",
                },
            )

        return own

    def can_see_hidden(self, college_id: UUID | None = None) -> bool:
        """
        Whether the caller may read a hidden row -- a post that is pending,
        held, removed or archived -- belonging to this college.

        Public content is cross-college for everybody, staff included. Hidden
        content is not: a moderator reviews their own campus and no other, so
        the college the row belongs to has to be passed in.

        Admin is platform-wide. Anyone else without the college gets False,
        so a caller that forgets to pass it fails closed.
        """
        if not self.can(Permission.MODERATE_POST):
            return False

        if self.is_platform_wide:
            return True

        return college_id is not None and college_id == self.college_id

    def owns(self, obj) -> bool:
        """
        Whether this row belongs to the caller. Reads `user_id`, falling back
        to `id` for the User rows themselves.
        """
        if self.user is None:
            return False

        owner_id = getattr(obj, "user_id", None)

        if owner_id is None:
            owner_id = getattr(obj, "id", None)

        return owner_id is not None and owner_id == self.id
