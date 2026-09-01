"""
Who counts as what.

Every role grouping in the codebase is defined here and nowhere else, so
changing who is considered staff is a one-line edit.
"""
from app.db.models import UserRole

# Roles that can act on other people's content or accounts.
STAFF_ROLES: frozenset[UserRole] = frozenset(
    {
        UserRole.admin,
        UserRole.moderator,
        UserRole.success_coach,
    }
)

# Roles that act across the whole platform rather than one college.
PLATFORM_ROLES: frozenset[UserRole] = frozenset({UserRole.admin})

# Staff whose authority stops at their own college.
COLLEGE_SCOPED_ROLES: frozenset[UserRole] = STAFF_ROLES - PLATFORM_ROLES

# Ordinary members.
MEMBER_ROLES: frozenset[UserRole] = frozenset(
    {
        UserRole.student,
        UserRole.alumni,
        UserRole.guest,
    }
)

ALL_ROLES: frozenset[UserRole] = frozenset(UserRole)


def is_staff(role: UserRole) -> bool:
    return role in STAFF_ROLES


def is_platform_wide(role: UserRole) -> bool:
    """True when the role is not confined to a single college."""
    return role in PLATFORM_ROLES
