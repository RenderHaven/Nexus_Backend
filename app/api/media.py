from fastapi import APIRouter, Depends, Query
from app.auth import get_current_user
from app.db.models import User
from app.media.service import MediaService

router = APIRouter()
media_service = MediaService()

@router.get("/signed_url")
async def get_signed_url(
    public_id: str | None = Query(None),
    dir: str = Query("other"),
    current_user: User = Depends(get_current_user),
):
    """Get a signature for uploading directly to Cloudinary from the frontend."""
    return media_service.get_signed_url(public_id, dir=dir)
