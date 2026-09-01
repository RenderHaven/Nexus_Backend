from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user
from app.db.models import User
from app.media.service import MEDIA_PURPOSES, MediaService

router = APIRouter()
media_service = MediaService()


@router.get("/signed_url")
async def get_signed_url(
    purpose: str = Query("post", description=f"One of: {', '.join(MEDIA_PURPOSES)}"),
    current_user: User = Depends(get_current_user),
):
    """Get everything needed to upload one file, plus the limits it must respect.

    Say what the upload is for and the server decides where it goes and what
    it will be called; the returned public_id is the only location the
    signature is valid for. Send that same public_id back with the post so the
    file can be managed later.

    max_file_size is the largest file accepted, and max_media_count is how many
    files one post may carry.
    """
    return media_service.get_signed_url(current_user.id, purpose=purpose)
