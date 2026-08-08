from app.auth import get_current_user
from app.services.post_intrections import PostInteractionsService
from uuid import UUID
from app.schemas.schemas import Post
from app.db.model import User
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.post import PostService
from app.db.session import get_db
router = APIRouter()


@router.get(
    "/top-engagement",
    response_model=list[Post],
)
async def get_top_engagement_posts(
    limit: int =10,
    db: AsyncSession = Depends(get_db),
):
    post_service = PostService(db)

    posts = await post_service.get_posts_by_engagement(limit)

    return posts

@router.get("/{post_id}",response_model=Post)
async def get_post(post_id:UUID,db:AsyncSession=Depends(get_db)):
    post_svc = PostService(db)    
    post = await post_svc.get_post(post_id)
    if not post:
        return {
            "message": "No posts found"
        }
    return post

@router.post("/{post_id}/like")
async def like_post(post_id:UUID, current_user: User = Depends(get_current_user), db:AsyncSession=Depends(get_db)):
    post_interaction_svc = PostInteractionsService(db)
    post_interaction = await post_interaction_svc.like(post_id, current_user.id)
    
    if not post_interaction:
        return {
            "message": "Post not liked"
        }
    return {
        "message": "Post liked successfully",
        "post_interaction": post_interaction
    }

@router.post("/{post_id}/unlike")
async def unlike_post(post_id:UUID, current_user: User = Depends(get_current_user), db:AsyncSession=Depends(get_db)):
    post_interaction_svc = PostInteractionsService(db)
    post_interaction = await post_interaction_svc.unlike(post_id,current_user.id)
    if not post_interaction:
        return {
            "message": "Post not liked"
        }
    return {
        "message": "Post liked successfully",
        "post_interaction": post_interaction
    }

@router.post("/{post_id}/comment")
async def comment_post(post_id:UUID,comment:str,current_user: User = Depends(get_current_user),db:AsyncSession=Depends(get_db)):
    post_interaction_svc = PostInteractionsService(db)
    post_interaction = await post_interaction_svc.comment(post_id,current_user.id,comment)
    if not post_interaction:
        return {
            "message": "Post not commented"
        }
    return {
        "message": "Post commented successfully",
        "post_interaction": post_interaction
    }

@router.post("/{comment_id}/reply")
async def comment_reply(comment_id:UUID,comment:str,current_user: User = Depends(get_current_user),db:AsyncSession=Depends(get_db)):
    post_interaction_svc = PostInteractionsService(db)
    post_interaction = await post_interaction_svc.add_comment_reply(current_user.id,comment_id,comment)
    if not post_interaction:
        return {
            "message": "Comment reply not added"
        }
    return {
        "message": "Comment reply added successfully",
        "post_interaction": post_interaction
    }

@router.post("/{comment_id}/edit")
async def edit_comment(comment_id:UUID,comment:str,current_user: User = Depends(get_current_user),db:AsyncSession=Depends(get_db)):
    post_interaction_svc = PostInteractionsService(db)
    post_interaction = await post_interaction_svc.edit_comment(current_user.id,comment_id,comment)
    if not post_interaction:
        return {
            "message": "Comment not edited"
        }
    return {
        "message": "Comment edited successfully",
        "post_interaction": post_interaction
    }

@router.post("/{comment_id}/delete")
async def delete_comment(comment_id:UUID,current_user: User = Depends(get_current_user),db:AsyncSession=Depends(get_db)):
    post_interaction_svc = PostInteractionsService(db)
    result = await post_interaction_svc.delete(current_user.id,comment_id)
    if result is None:
        return {
            "message": "Comment not deleted"
        }
    return {
        "message": "Comment deleted successfully",
        "post_interaction": result
    }

