with open("app/domains/post/service.py", "r") as f:
    content = f.read()

# Replace ReactionStorage with LikeService
content = content.replace(
    "from app.domains.reaction.storage import ReactionStorage\n        reaction_store = ReactionStorage(self.db)",
    "from app.domains.reaction.service import LikeService\n        like_svc = LikeService(self.db)"
)
content = content.replace("likes = await reaction_store.are_liked(p_ids, user_id)", "likes = await like_svc.are_liked(p_ids, user_id)")

# Replace CollaborationStorage with CollabStatusService
content = content.replace(
    "from app.domains.collaboration.storage import CollaborationStorage\n            collab_store = CollaborationStorage(self.db)",
    "from app.domains.collaboration.service import CollabStatusService\n            collab_status_svc = CollabStatusService(self.db)"
)
content = content.replace("collab_statuses = await collab_store.get_statuses(collab_ids, user_id)", "collab_statuses = await collab_status_svc.get_statuses(collab_ids, user_id)")

with open("app/domains/post/service.py", "w") as f:
    f.write(content)
