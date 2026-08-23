from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domains.user.service import UserService
from app.schemas.schemas import User as UserSchema
from app.auth.deps import get_current_user
from app.db.model import User as UserModel

router = APIRouter()


@router.get("/me", response_model=UserSchema)
async def get_me(current_user: UserModel = Depends(get_current_user)):
    return UserSchema.model_validate(current_user)


@router.get("/{user_id}", response_model=UserSchema)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    user = await service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user
