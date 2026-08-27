from uuid import UUID
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.auth.deps import get_current_user_id_optional
from app.db.models import User
from app.db.session import get_db
from app.domains.comments.service import CommentService
from app.domains.reaction.service import ReactionService
from app.domains.post.service import PostService
from app.domains.types.enum import PostType
from app.domains.types.service import PostTypeService
from app.schemas.schemas import Post, PostIdResponse

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from app.schemas.schemas import PostCreate, PostUpdate, MediaType
from app.db.models import Post as DBPost, PostMedia as DBPostMedia

router = APIRouter()

class PostIDsRequest(BaseModel):
    post_ids: list[UUID]

def create_db_post_from_schema(payload: PostCreate, current_user: User) -> DBPost:
    db_post = DBPost(
        user_id=current_user.id,
        college_id=current_user.college_id,
        category_id=payload.category_id,
        type=payload.type,
        title=payload.title,
        content=payload.content,
        date_at=payload.date_at,
        restricted_to_college_id=payload.restricted_to_college_id,
        resources=[res.model_dump() for res in payload.resources] if payload.resources else None,
        action_status=payload.action_status,
    )
    if payload.media_ids:
        for i, media_id in enumerate(payload.media_ids):
            db_post.media.append(DBPostMedia(url=media_id, media_type=MediaType.image, position=i+1))
    return db_post

def make_media_permanent_bg(media_ids: list[str]):
    if not media_ids:
        return
    from app.media.service import MediaService
    MediaService().make_permanent(media_ids)



@router.post("/", response_model=PostIdResponse)
async def add_post(
    payload: PostCreate,
    bg_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post_svc = PostService(db)
    
    db_post = create_db_post_from_schema(payload, current_user)
    
    import uuid
    db_post.id = uuid.uuid4()
    
    created_post_id = await post_svc.add_post(db_post)
    if payload.media_ids:
        bg_tasks.add_task(make_media_permanent_bg, payload.media_ids)
    return {
        "status": "success",
        "message": "Post added successfully",
        "post_id": created_post_id
    }

@router.post("/events", response_model=PostIdResponse)
async def add_event(
    payload: PostCreate,
    bg_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role.value not in ["admin", "success_coach"]:
        raise HTTPException(status_code=403, detail="Not authorized to create events")
    payload.type = PostType.event
    return await add_post(payload, bg_tasks, current_user, db)

@router.post("/collaborations", response_model=PostIdResponse)
async def add_collaboration(
    payload: PostCreate,
    bg_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payload.type = PostType.collaboration
    return await add_post(payload, bg_tasks, current_user, db)

@router.post("/opportunities", response_model=PostIdResponse)
async def add_opportunity(
    payload: PostCreate,
    bg_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role.value not in ["admin", "success_coach"]:
        raise HTTPException(status_code=403, detail="Not authorized to create opportunities")
    payload.type = PostType.opportunity
    return await add_post(payload, bg_tasks, current_user, db)

@router.put("/{post_id}", response_model=PostIdResponse)
async def edit_post(
    post_id: UUID,
    payload: PostUpdate,
    bg_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post_svc = PostService(db)
    
    existing_post = await post_svc.post_store.post_repo.get_by_id(post_id)
    if not existing_post or existing_post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized or not found")
        
    if payload.title is not None:
        existing_post.title = payload.title
    if payload.content is not None:
        existing_post.content = payload.content
    if payload.category_id is not None:
        existing_post.category_id = payload.category_id
    if payload.type is not None:
        existing_post.type = payload.type
    if payload.date_at is not None:
        existing_post.date_at = payload.date_at
    if payload.restricted_to_college_id is not None:
        existing_post.restricted_to_college_id = payload.restricted_to_college_id
    if payload.resources is not None:
        existing_post.resources = [res.model_dump() for res in payload.resources]
    if payload.action_status is not None:
        existing_post.action_status = payload.action_status
    if payload.status is not None:
        existing_post.status = payload.status
    if payload.moderation_status is not None:
        existing_post.moderation_status = payload.moderation_status
    if payload.is_active is not None:
        existing_post.is_active = payload.is_active
        
    if payload.media_ids is not None:
        from app.db.models import PostMedia as DBPostMedia
        existing_post.media = []
        for i, media_id in enumerate(payload.media_ids):
            existing_post.media.append(DBPostMedia(url=media_id, media_type=MediaType.image, position=i+1))
        bg_tasks.add_task(make_media_permanent_bg, payload.media_ids)
        
    updated_post_id = await post_svc.update_post(existing_post)
    return {
        "status": "success",
        "message": "Post updated successfully",
        "post_id": updated_post_id
    }


@router.get("/{post_id}", response_model=Post)
async def get_post(
    post_id: UUID,
    user_id: UUID | None = Depends(get_current_user_id_optional),
    db: AsyncSession = Depends(get_db),
):
    post_svc = PostService(db)
    post = await post_svc.get_post(post_id, user_id)
    if not post:
        raise HTTPException(status_code=404, detail="No post found")
    return post


@router.post("/batch", response_model=list[Post])
async def get_posts(
    payload: PostIDsRequest,
    user_id: UUID | None = Depends(get_current_user_id_optional),
    db: AsyncSession = Depends(get_db),
):
    post_svc = PostService(db)
    return await post_svc.get_posts(
        payload.post_ids,
        user_id,
    )


@router.get("/{post_id}/comment_ids")
async def get_comment_ids(
    post_id: UUID,
    cursor: str | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    comment_svc = CommentService(db)
    comment_ids, next_cursor = await comment_svc.get_comment_ids(post_id, cursor=cursor, limit=limit)
    if not comment_ids:
        return {"comment_ids": [], "next_cursor": None}
    return {"comment_ids": comment_ids, "next_cursor": next_cursor}


from app.schemas.schemas import CommentRequest

@router.post("/{post_id}/comment")
async def comment_post(
    post_id: UUID,
    payload: CommentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    comment_svc = CommentService(db)
    post_interaction = await comment_svc.comment(post_id, current_user.id, payload.comment)
    if not post_interaction:
        return {"status": "error", "message": "Post not commented"}
    return {
        "status": "success",
        "message": "Post commented successfully",
        "comment_id": post_interaction.get("comment_id"),
    }


@router.post("/{post_id}/like")
async def like_post(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    reaction_svc = ReactionService(db)
    post_reaction = await reaction_svc.like(post_id, current_user.id)
    if not post_reaction:
        return {"status": "error", "message": "Post not liked"}
    return {
        "status": "success",
        "message": "Post liked successfully",
        "post_id": post_id,
    }


@router.post("/{post_id}/unlike")
async def unlike_post(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    reaction_svc = ReactionService(db)
    post_reaction = await reaction_svc.unlike(post_id, current_user.id)
    if not post_reaction:
        return {"status": "error", "message": "Post not unliked"}
    return {
        "status": "success",
        "message": "Post unliked successfully",
        "post_id": post_id,
    }


@router.get("/type/{post_type}/post_ids")
async def get_type_post_ids(
    post_type: PostType,
    user_id: UUID | None = Depends(get_current_user_id_optional),
    cursor: str | None = None,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    post_type_svc = PostTypeService(db)
    post_ids, next_cursor = await post_type_svc.get_type_post_ids(
        post_type=post_type,
        user_id=user_id,
        cursor_key=cursor,
        limit=limit,
    )
    if not post_ids:
        return {
            "posts": [],
            "next_cursor": None,
        }
    return {
        "posts": post_ids,
        "next_cursor": next_cursor,
    }
