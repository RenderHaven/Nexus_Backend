from app.db.models import ModerationStatus, PostStatus


def compute_is_active(
    status: PostStatus | str,
    moderation_status: ModerationStatus | str,
) -> bool:
    """
    A post is publicly visible (is_active) only when its owner keeps it
    published AND a moderator has approved it.

    is_active is never set directly; it is always derived from these two
    fields so pools and public reads share one definition of "visible".
    """
    return (
        status == PostStatus.published
        and moderation_status == ModerationStatus.approved
    )


def apply_is_active(post) -> None:
    """Recompute and assign is_active on a Post model instance."""
    post.is_active = compute_is_active(post.status, post.moderation_status)
