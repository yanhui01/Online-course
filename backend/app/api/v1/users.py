"""用户 API 路由"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.user import User
from app.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["用户"])


@router.get("/me", response_model=UserResponse)
async def get_me(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户信息"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    return user
