"""认证与安全：JWT 创建/验证、密码哈希、Token 黑名单"""

from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from redis.asyncio import Redis

from app.config import settings
from app.core.redis import get_redis

bearer_scheme = HTTPBearer(auto_error=False)


# ============================================================
# 密码哈希（直接使用 bcrypt，避免 passlib 兼容性问题）
# ============================================================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ============================================================
# JWT
# ============================================================

def create_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    to_encode.update({"exp": datetime.now(timezone.utc) + expires_delta})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: str) -> str:
    return create_token(
        {"sub": user_id, "type": "access"},
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: str) -> str:
    return create_token(
        {"sub": user_id, "type": "refresh"},
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证凭据")


# ============================================================
# Token 黑名单（Redis，Redis 不可用时跳过）
# ============================================================

async def blacklist_token(redis: Redis | None, token: str, ttl: int = 3600 * 24 * 7):
    """将 token 加入黑名单"""
    if redis is None:
        return
    try:
        await redis.setex(f"blacklist:token:{token}", ttl, "1")
    except Exception:
        pass


async def is_token_blacklisted(redis: Redis | None, token: str) -> bool:
    if redis is None:
        return False
    try:
        return await redis.exists(f"blacklist:token:{token}") > 0
    except Exception:
        return False


# ============================================================
# 获取当前用户 ID（FastAPI 依赖）
# ============================================================

async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    redis: Redis | None = Depends(get_redis),
) -> str:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")

    token = credentials.credentials

    if await is_token_blacklisted(redis, token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 已失效")

    payload = decode_token(token)

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请使用 Access Token")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证凭据")

    return user_id
