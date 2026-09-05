from app.db.models import ModerationStatus, PostStatus


def compute_is_active(
    status: PostStatus | str,
    moderation_status: ModerationStatus | str,
    author_is_active: bool = True,
) -> bool:
    """
    A post is publicly visible (is_active) only when its owner keeps it
    published, a moderator has approved it, AND its author's account is still
    active.

    is_active is never set directly; it is always derived from these fields so
    pools, the search index and public reads share one definition of
    "visible".

    author_is_active defaults to True because most callers are acting on a
    post whose author is signing in to act on it. The paths that can be
    reached while an author is deactivated -- moderation decisions, and the
    deactivation sweep itself -- pass it explicitly.
    """
    return (
        status == PostStatus.published
        and moderation_status == ModerationStatus.approved
        and author_is_active
    )


def apply_is_active(post, author_is_active: bool = True) -> None:
    """Recompute and assign is_active on a Post model instance."""
    post.is_active = compute_is_active(
        post.status,
        post.moderation_status,
        author_is_active,
    )
