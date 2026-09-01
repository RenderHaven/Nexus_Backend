"""Rules about what kinds of content need elevated rights."""
from app.db.models import PostType

# Post types only staff may create. Everything else is open to any member.
RESTRICTED_POST_TYPES: frozenset[PostType] = frozenset(
    {
        PostType.event,
        PostType.opportunity,
    }
)
