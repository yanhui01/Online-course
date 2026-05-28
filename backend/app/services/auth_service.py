"""认证服务"""

from typing import Optional

from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    blacklist_token,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import RegisterRequest, TokenResponse


async def register(db: AsyncSession, data: RegisterRequest) -> User:
    """用户注册"""
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")

    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="邮箱已被注册")

    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    await db.flush()
    return user


async def login(db: AsyncSession, username: str, password: str) -> TokenResponse:
    """用户登录"""
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


async def refresh_token(redis: Optional[Redis], refresh_token_str: str) -> TokenResponse:
    """刷新 Token（旧的 refresh_token 加入黑名单）"""
    payload = decode_token(refresh_token_str)

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请使用 Refresh Token")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证凭据")

    await blacklist_token(redis, refresh_token_str)

    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


async def logout(redis: Optional[Redis], access_token: str, refresh_token: str | None = None):
    """登出：将 token 加入黑名单"""
    await blacklist_token(redis, access_token)
    if refresh_token:
        await blacklist_token(redis, refresh_token)
