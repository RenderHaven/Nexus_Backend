import enum

class UserRole(str, enum.Enum):
    admin = "admin"
    moderator = "moderator"
    success_coach = "success_coach"
    student = "student"
    alumni = "alumni"
    guest = "guest"


class IdentityLevel(str, enum.Enum):
    spark = "spark"
    kindler = "kindler"
    amplifier = "amplifier"
    pathfinder = "pathfinder"
    horizon = "horizon"
    constellation = "constellation"


class PostType(str, enum.Enum):
    achievement = "achievement"
    knowledge = "knowledge"
    collaboration = "collaboration"
    event = "event"
    opportunity = "opportunity"
    spark = "spark"


class PostStatus(str, enum.Enum):
    published = "published"
    archived = "archived"
    deleted = "deleted"


class ModerationStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    hold = "hold"
    removed = "removed"


class ModerationAction(str, enum.Enum):
    approve = "approve"
    hold = "hold"
    remove = "remove"


class ReactionType(str, enum.Enum):
    liked = "liked"
    curious = "curious"
    want_to_try = "want_to_try"


class MediaType(str, enum.Enum):
    image = "image"
    video = "video"
    gif = "gif"


class ActionStatus(str, enum.Enum):
    open = "open"
    closed = "closed"


class CollaborationRequestStatus(str, enum.Enum):
    requested = "requested"
    accepted = "accepted"
    rejected = "rejected"
    revoked="revoked"


class ConversationStatus(str, enum.Enum):
    active = "active"
    closed = "closed"


class MessageType(str, enum.Enum):
    text = "text"
    link = "link"
    file = "file"


# Legacy aliases for backward compatibility
InteractionType = ReactionType
CollaborationStatus = ActionStatus


# =========================
# Models
# =========================

# Legacy aliases for backward compatibility
InteractionType = ReactionType
CollaborationStatus = ActionStatus
