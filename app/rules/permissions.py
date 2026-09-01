"""
What each role is allowed to do.

Two tables drive every authorisation decision in the app:

  PERMISSIONS      which roles hold a permission at all
  COLLEGE_SCOPED   which permissions a non-platform role may only use
                   inside their own college

To change who can do what, edit these tables. Nothing else needs to move.
"""
from enum import StrEnum
from uuid import UUID

from fastapi import HTTPException

from app.db.models import UserRole
from app.rules.roles import (
    ALL_ROLES,
    MEMBER_ROLES,
    PLATFORM_ROLES,
    STAFF_ROLES,
    is_platform_wide,
)


class Permission(StrEnum):
    # Posts
    CREATE_RESTRICTED_POST = "create_restricted_post"
    MODERATE_POST = "moderate_post"
    DELETE_ANY_POST = "delete_any_post"

    # Users
    CREATE_USER = "create_user"

    # Colleges
    CREATE_COLLEGE = "create_college"
    EDIT_COLLEGE = "edit_college"


PERMISSIONS: dict[Permission, frozenset[UserRole]] = {
    Permission.CREATE_RESTRICTED_POST: STAFF_ROLES,
    Permission.MODERATE_POST: STAFF_ROLES,
    Permission.DELETE_ANY_POST: STAFF_ROLES,
    Permission.CREATE_USER: STAFF_ROLES,
    Permission.CREATE_COLLEGE: PLATFORM_ROLES,
    Permission.EDIT_COLLEGE: STAFF_ROLES,
}

# Permissions a college-scoped role may only exercise on their own college.
# A platform role (admin) is never limited by these.
COLLEGE_SCOPED: frozenset[Permission] = frozenset(
    {
        Permission.CREATE_USER,
        Permission.EDIT_COLLEGE,
    }
)

# Which roles each role may hand out when creating an account.
ASSIGNABLE_ROLES: dict[UserRole, frozenset[UserRole]] = {
    UserRole.admin: ALL_ROLES,
    UserRole.moderator: MEMBER_ROLES,
    UserRole.success_coach: MEMBER_ROLES,
}


def _forbidden(message: str) -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={"code": "forbidden", "message": message},
    )


# ----------------------------------------------------------------------
# Checks
# ----------------------------------------------------------------------

def has_permission(user, permission: Permission) -> bool:
    return user.role in PERMISSIONS.get(permission, frozenset())


def can_act_on_college(user, permission: Permission, college_id: UUID | None) -> bool:
    """
    Whether the permission may be used against this college. Platform roles
    may act anywhere; everyone else only inside their own college.
    """
    if not has_permission(user, permission):
        return False

    if permission not in COLLEGE_SCOPED or is_platform_wide(user.role):
        return True

    return college_id is not None and user.college_id == college_id


def can_assign_role(user, target_role: UserRole) -> bool:
    return target_role in ASSIGNABLE_ROLES.get(user.role, frozenset())


# ----------------------------------------------------------------------
# Guards
# ----------------------------------------------------------------------

def require_permission(user, permission: Permission):
    if not has_permission(user, permission):
        raise _forbidden("Not authorized to perform this action")
    return user


def require_college_permission(user, permission: Permission, college_id: UUID | None):
    require_permission(user, permission)

    if not can_act_on_college(user, permission, college_id):
        raise _forbidden("You can only do this within your own college")

    return user


def require_assignable_role(user, target_role: UserRole):
    if not can_assign_role(user, target_role):
        raise _forbidden(f"You cannot give someone the {target_role.value} role")
    return user
