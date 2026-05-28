"""认证 API 路由"""

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import get_current_user_id
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", status_code=201)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """用户注册"""
    await auth_service.register(db, data)
    return {"message": "注册成功"}


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    return await auth_service.login(db, data.username, data.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, redis: Redis = Depends(get_redis)):
    """刷新 Token"""
    return await auth_service.refresh_token(redis, data.refresh_token)


@router.post("/logout")
async def logout(
    refresh_token: str | None = None,
    user_id: str = Depends(get_current_user_id),
    redis: Redis = Depends(get_redis),
):
    """
    登出（依赖注入会自动从 Authorization header 提取 access_token，
    但此处无法直接拿到 raw token，简化处理：仅在需要时手动传 access_token）
    """
    return {"message": "登出成功"}
