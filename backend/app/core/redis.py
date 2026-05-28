"""Redis 连接管理 + ARQ 任务队列配置（可选依赖）"""

from arq.connections import RedisSettings
from redis.asyncio import Redis

from app.config import settings

# ARQ 任务队列配置
arq_settings = RedisSettings(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    database=settings.REDIS_DB,
)

# 通用 Redis 连接
redis_client: Redis | None = None
_redis_available: bool | None = None


async def is_redis_available() -> bool:
    """检测 Redis 是否可用"""
    global _redis_available
    if _redis_available is not None:
        return _redis_available
    try:
        r = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            socket_connect_timeout=2,
        )
        await r.ping()
        await r.close()
        _redis_available = True
    except Exception:
        _redis_available = False
    return _redis_available


async def get_redis() -> Redis | None:
    """获取 Redis 客户端，不可用时返回 None"""
    global redis_client
    if redis_client is None:
        try:
            redis_client = Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=2,
            )
            await redis_client.ping()
        except Exception:
            redis_client = None
    return redis_client


async def close_redis():
    """关闭 Redis 连接"""
    global redis_client, _redis_available
    if redis_client is not None:
        try:
            await redis_client.close()
        except Exception:
            pass
        redis_client = None
    _redis_available = None
