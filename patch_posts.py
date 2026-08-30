with open("app/api/posts.py", "r") as f:
    content = f.read()

import_stmt = "\nfrom app.domains.collaboration.schemas import CollabStatusResult, CollabStatusUpdate\nfrom app.domains.collaboration.service import CollaborationService\n"

endpoint = """
@router.post("/{post_id}/collab_status", response_model=CollabStatusResult)
async def update_collab_status(
    post_id: UUID,
    payload: CollabStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    collab_svc = CollaborationService(db)
    result = await collab_svc.update_status(post_id, current_user.id, payload.status)
    return result
"""

# add imports near ReactionAction
content = content.replace("from app.domains.reaction.schemas import ReactionResult, ReactionAction", "from app.domains.reaction.schemas import ReactionResult, ReactionAction" + import_stmt)

# add endpoint near like_post
content = content.replace("@router.post(\"/{post_id}/like\", response_model=ReactionResult)", endpoint + "\n\n@router.post(\"/{post_id}/like\", response_model=ReactionResult)")

with open("app/api/posts.py", "w") as f:
    f.write(content)
